"""Offline Persian workflow adapter. Never edits, applies, persists or publishes."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ig-human'))
from persian_fact_checks import check_facts
from persian_review import review
from persian_tone import review_tone
from persian_rewrite import suggest
from persian_simplify import simplify
from persian_rewrite_checks import mark_conflicts, validate_selection

LIMITATIONS = [
    'نبود یافته تأیید کیفیت یا صحت نیست؛ حفظ معنا تضمین نمی‌شود.',
    'نام بدون معرفی صریح حدس زده نمی‌شود؛ protected_terms را کامل کنید.',
    'واقعیت‌های تأییدشده فقط به صورت عین عبارت محافظت می‌شوند؛ تطابق معنایی ادعا نیازمند انسان است.',
    'پذیرش پیشنهاد فقط ثبت تصمیم در خروجی است؛ متن و فایل تغییر نمی‌کنند.',
    'پیوستگی داستان، نفی و شرط بین بخش‌ها و مرز نقل‌قول‌ها نیازمند بررسی انسانی است.',
]
FIELDS = {'format', 'topic', 'goal', 'audience', 'target_tone', 'target_address',
          'verified_facts', 'protected_terms', 'optional_cta', 'draft'}


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def object_hash(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def exact_keys(value, allowed, required):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError('invalid or missing fields')


def string(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('expected nonempty string')


def sections(request):
    exact_keys(request, FIELDS, FIELDS - {'draft', 'optional_cta'})
    if request['format'] not in ('caption', 'reel', 'story'):
        raise ValueError('invalid format')
    if request['target_tone'] not in ('formal', 'semi-formal', 'colloquial'):
        raise ValueError('invalid tone')
    if request['target_address'] not in ('shoma', 'to', 'unspecified'):
        raise ValueError('invalid address')
    for key in ('topic', 'goal', 'audience'):
        string(request[key])
    for key in ('verified_facts', 'protected_terms'):
        if not isinstance(request[key], list):
            raise ValueError('expected string list')
        for item in request[key]:
            string(item)
    if request.get('optional_cta') is not None:
        string(request['optional_cta'])
    draft = request.get('draft')
    if draft is None:
        return []
    fmt = request['format']
    if fmt == 'caption':
        exact_keys(draft, {'text'}, {'text'})
        values = [('caption.text', draft['text'])]
    elif fmt == 'reel':
        keys = ('hook', 'spoken_script', 'on_screen_text', 'ending')
        exact_keys(draft, keys, keys)
        values = [('reel.' + key, draft[key]) for key in keys]
    else:
        exact_keys(draft, {'cards'}, {'cards'})
        if not isinstance(draft['cards'], list) or not draft['cards']:
            raise ValueError('expected ordered cards')
        values = []
        for number, card in enumerate(draft['cards'], 1):
            exact_keys(card, {'number', 'text'}, {'number', 'text'})
            if type(card['number']) is not int or card['number'] != number:
                raise ValueError('cards must be consecutively numbered from 1')
            values.append((f'story.card.{number}', card['text']))
    for _, text in values:
        string(text)
    return values


def section_report(section_id, text, request):
    protect = list(dict.fromkeys(request['protected_terms'] + request['verified_facts']))
    raw = {'persian_review': review(text),
           'persian_tone': review_tone(text, request['target_tone'], request['target_address']),
           'persian_rewrite': suggest(text, protect),
           'persian_simplify': simplify(text, protect, request['target_tone'])}
    result = dict(section_id=section_id, source_text=text, source_hash=digest(text),
                  findings=[], suggestions=[], guidance=[], abstentions=[], limitations=[], raw_reports=raw)
    for name, report in raw.items():
        for category in ('findings', 'suggestions', 'guidance', 'abstentions'):
            for original in report.get(category, []):
                item = deepcopy(original)
                item.update(tool=name, section_id=section_id, source_hash=result['source_hash'])
                if category == 'suggestions':
                    item['id'] = section_id + ':' + name + ':' + original['id']
                result[category].append(item)
        result['limitations'].extend(report.get('limitations', []))
    if raw['persian_tone']['assessment'] == 'insufficient_evidence':
        result['abstentions'].append(dict(tool='persian_tone', reason='insufficient_evidence',
            section_id=section_id, source_hash=result['source_hash']))
    mark_conflicts(result['suggestions'])
    result['limitations'] = list(dict.fromkeys(result['limitations'] + [raw['persian_review']['notice']]))
    return result


def story_sequence(values, request):
    text, mapping = '', []
    for sid, value in values:
        if mapping:
            text += '\n'
        start = len(text)
        text += value
        mapping.append(dict(section_id=sid, start=start, end=len(text), source_hash=digest(value)))
    raw = review_tone(text, None, 'unspecified')
    findings = []
    for original in raw['findings']:
        if original['rule_id'] != 'fa-address-shift':
            continue
        item = deepcopy(original)
        for evidence in item['evidence']:
            refs = []
            for span in mapping:
                a, b = max(span['start'], evidence['start']), min(span['end'], evidence['end'])
                if a < b:
                    refs.append(dict(section_id=span['section_id'], source_hash=span['source_hash'],
                                     start=a-span['start'], end=b-span['start']))
            evidence['section_spans'] = refs
        item.update(section_id='story.sequence', source_hash=digest(text))
        findings.append(item)
    return dict(section_id='story.sequence', source_text=text, source_hash=digest(text),
                section_map=mapping, findings=findings, suggestions=[], guidance=[],
                abstentions=[{'reason': 'insufficient_evidence', 'section_id': 'story.sequence',
                             'source_hash': digest(text)}] if raw['assessment']=='insufficient_evidence' else [],
                limitations=list(LIMITATIONS), raw_reports={'persian_tone': raw})


def decisions_for(report, decisions):
    if not isinstance(decisions, list):
        raise ValueError('decisions must be a list')
    sections_by_id = {s['section_id']: s for s in report['sections']}
    seen, accepted, receipts = set(), {}, []
    for decision in decisions:
        keys = {'section_id', 'suggestion_id', 'source_hash', 'request_hash', 'start', 'end', 'before', 'action'}
        exact_keys(decision, keys, keys)
        for key in ('section_id', 'suggestion_id', 'source_hash', 'request_hash', 'before', 'action'):
            if not isinstance(decision[key], str):
                raise ValueError(f'decision.{key} must be a string')
        if decision['action'] not in ('accept', 'reject'):
            raise ValueError('explicit accept/reject required')
        section = sections_by_id.get(decision['section_id'])
        if section is None or decision['source_hash'] != section['source_hash'] or decision['request_hash'] != report['source_hash']:
            raise ValueError('stale or unknown source version')
        candidates = {s['id']: s for s in section['suggestions']}
        candidate = candidates.get(decision['suggestion_id'])
        if candidate is None or candidate['id'] in seen:
            raise ValueError('unknown or duplicate suggestion')
        seen.add(candidate['id'])
        if any(type(decision[k]) is not int for k in ('start','end')):
            raise ValueError('offset must be integer')
        if any(decision[k] != candidate[k] for k in ('start','end','before')):
            raise ValueError('source span mismatch')
        if section['source_text'][decision['start']:decision['end']] != decision['before']:
            raise ValueError('before mismatch')
        if decision['action'] == 'accept':
            accepted.setdefault(section['section_id'], []).append(candidate['id'])
        receipts.append(dict(decision, replacement=candidate['replacement'], applied=False))
    for sid, ids in accepted.items():
        validate_selection(sections_by_id[sid]['suggestions'], ids)
    return receipts


def coordinate(request, decisions=None):
    values = sections(request)
    report = dict(schema_version=1, engine='offline_workflow', source_hash=object_hash(request),
                  brief={k: deepcopy(v) for k,v in request.items() if k!='draft'},
                  mode='review' if values else 'brief_only', sections=[],
                  findings=[], suggestions=[], guidance=[], abstentions=[], limitations=list(LIMITATIONS))
    if not values:
        report['generation_instruction'] = {
            'recipient': 'language_model_or_human', 'format': request['format'],
            'constraints': ['فقط از اطلاعات تأییدشده استفاده کنید؛ ادعای تازه نسازید.',
                'لحن و خطاب مستقل، CTA اختیاری، نام و عدد و نفی و شرط حفظ شوند.',
                'کپشن: text؛ ریلز: hook/spoken_script/on_screen_text/ending؛ استوری: cards با number و text.'],
            'brief': deepcopy(report['brief']), 'generated_draft': False}
    else:
        report['sections'] = [section_report(sid, text, request) for sid,text in values]
        if request['format'] == 'story':
            report['sequence_review'] = story_sequence(values, request)
        for section in report['sections'] + ([report['sequence_review']] if 'sequence_review' in report else []):
            for category in ('findings','suggestions','guidance','abstentions'):
                report[category].extend(deepcopy(section[category]))
    report['fact_checks'] = check_facts(request['verified_facts'], request['protected_terms'],
                                      report['sections'], report['source_hash'])
    report['decisions'] = decisions_for(report, [] if decisions is None else decisions)
    report['applied'] = False
    return report


def read_json(path):
    raw = sys.stdin.buffer.read() if path == '-' else Path(path).read_bytes()
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)


def main():
    parser = argparse.ArgumentParser(description='هماهنگ‌کننده آفلاین فارسی؛ فقط گزارش JSON، بدون اعمال تغییر')
    parser.add_argument('input', nargs='?', default='-')
    parser.add_argument('--decisions', help='فایل JSON تصمیم‌های صریح؛ متن را تغییر نمی‌دهد')
    args = parser.parse_args()
    if args.input == '-' and args.decisions == '-':
        parser.error('stdin cannot hold both input and decisions')
    try:
        report = coordinate(read_json(args.input), read_json(args.decisions) if args.decisions else None)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
