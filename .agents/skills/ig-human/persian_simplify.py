"""Offline, opt-in language suggestions. All replacements require confirmation."""
import json
from pathlib import Path
import re

from persian_protection import protected_spans, overlaps
from persian_review import BOUNDARY
from persian_simplify_checks import validate, sentence_spans, BARRIER

RULES = Path(__file__).with_name('persian_simplify_rules.json')
LIMITATIONS = ['قواعد محدودند و حفظ معنا یا طبیعی‌بودن تضمین نمی‌شود.',
               'کنایه، حقوق، نام‌ها و ساختار نحوی پوشش جامع ندارند؛ پیشنهادها نیازمند تأیید انسان‌اند.',
               'هیچ تغییر خطاب یا شکسته‌نویسی خودکار و هیچ اعمالی روی فایل انجام نمی‌شود.']


def simplify(text, protect=(), target_tone=None):
    if target_tone not in (None, 'formal', 'semi-formal', 'colloquial'):
        raise ValueError('unsupported target tone')
    spans = protected_spans(text, protect)
    rules = json.loads(RULES.read_text(encoding='utf-8'))['rules']
    suggestions, guidance, abstentions = [], [], []
    for original in rules:
        rule = dict(original)
        rule['replacement'] = rule.get('tone_replacements', {}).get(target_tone, rule['replacement'])
        pattern = re.compile(r'(?<!' + BOUNDARY + r')(?:' + rule['pattern'] + r')(?!' + BOUNDARY + r')')
        for match in pattern.finditer(text):
            replacement = rule['replacement'].format(**match.groupdict())
            # Neutral respectful forms also work in colloquial writing; never infer "تو".
            candidate = dict(rule_id=rule['id'], start=match.start(), end=match.end(), before=match.group(),
                             replacement=replacement, reason=rule['reason'], requires_confirmation=True,
                             category='linguistic')
            error = validate(text, candidate, spans, rule)
            if error:
                abstentions.append(dict(start=match.start(), end=match.end(), before=match.group(),
                                        rule_id=rule['id'], reason=error))
            else:
                suggestions.append(candidate)
    for start, end in sentence_spans(text):
        sentence = text[start:end]
        heavy = re.search(r'می[‌ ]باشد|انجام می[‌ ]پذیرد|صورت می[‌ ]گیرد|خواهشمند است|مقتضی است|به استحضار|به عمل|به میزان|ارسال فرمایید', sentence)
        long = len(sentence.split()) > 35 and bool(re.search(r'[\u0621-\u06cc]', sentence))
        # Protected quotations/dialogue are not attributed to the author.
        excluded = [s for s in spans if s['reason'] in ('quotation', 'dialogue', 'code', 'user_protected', 'reported_speech')]
        if (heavy or long) and not overlaps(start, end, excluded) and not any(start <= s['start'] and s['end'] <= end for s in suggestions):
            guidance.append(dict(start=start, end=end, before=sentence, replacement=None,
                reason='ساختار سنگین یا حساس؛ فاعل، رابطهٔ بندها و لحن را انسانی بررسی کنید.',
                requires_confirmation=True, rule_id='fa-human-structure'))
    # One entry per location/replacement; prefer the longest candidate at a shared start.
    unique = {(s['start'], s['end'], s['replacement']): s for s in suggestions}
    suggestions = sorted(unique.values(), key=lambda s: (s['start'], -s['end'], s['rule_id']))
    for i, s in enumerate(suggestions, 1):
        s['id'] = 'l' + str(i)
        s['conflicts_with'] = []
        s['checks'] = {'semantic_review': 'required', 'limited_rule_checks': 'passed'}
    return dict(target_tone=target_tone, suggestions=suggestions, guidance=guidance,
                abstentions=abstentions, limitations=list(LIMITATIONS),
                status='suggestions_available' if suggestions else 'guidance_only' if guidance else 'insufficient_context' if abstentions else 'no_suggestions')
