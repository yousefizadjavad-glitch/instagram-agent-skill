"""Opt-in Persian tone evidence; no rewriting, scores or language inference."""
import re

from persian_review import BOUNDARY, quote_spans

LIMITATIONS = [
    'قواعد محدودند؛ نبود یافته تأیید یکدستی لحن نیست.',
    'عمدی‌بودن تغییر، مخاطب ضمنی، طنز و گفتار غیرمستقیم به بررسی انسانی نیاز دارند.',
    'دیالوگ فقط با برچسب‌های صریح شناخته می‌شود؛ گویش‌ها و صرف کامل پوشش داده نمی‌شوند.',
]


def bounded(pattern):
    return re.compile(r'(?<!' + BOUNDARY + r')(?:' + pattern + r')(?!' + BOUNDARY + r')')


ADMIN = bounded(r'مقتضی است|(?:بدین[‌ ]وسیله )?به (?:اطلاع|استحضار) می[‌ ]رساند|(?:اقدامات لازم را )?مبذول فرمایید')
COLLOQUIAL = bounded(r'می[‌ ]تونی(?:ن)?|می[‌ ]تونین|بزن بریم|یادت نره|(?:فرم|سفارش|رنگ|اندازه|شماره) رو')
# A small explicit grammar: prepositional "تو خونه/این ویدئو" never matches.
ADDRESS = bounded(r'(?P<pronoun>شما|تو)\s+(?:می[‌ ]توانید|می[‌ ]تونی(?:ن)?|می[‌ ]تونین|(?:رنگ را |اندازه را )?انتخاب کنید|بخوانید|پاسخ بده|فرم را تکمیل کنید|شمارهٔ سفارش را بفرستید)')
DIALOGUE = re.compile(r'(?m)^\s*(?:مشتری|پشتیبان|گوینده(?:ٔ? [۱۲12])?|کاربر|فروشنده)\s*[:：][^\n]*')
REPORTED = bounded(r'(?:گفت|نوشت|پرسید|گفتند)\s*[:：]?')
AUDIENCE = bounded(r'(?:والدین|دانش[‌ ]آموز|مشتری|همکار|دوست|دوستان|مخاطب|مخاطبان) عزیز')


def review_tone(text, target_tone=None, target_address='unspecified'):
    if target_tone not in (None, 'formal', 'semi-formal', 'colloquial'):
        raise ValueError('unsupported target tone')
    if target_address not in ('unspecified', 'shoma', 'to'):
        raise ValueError('unsupported target address')
    analysis = text.translate(str.maketrans({'ي': 'ی', 'ك': 'ک'}))
    excluded = []

    def exclude(start, end, reason):
        excluded.append({'start': start, 'end': end, 'reason': reason})

    for start, end in quote_spans(text):
        exclude(start, end, 'quotation')
    for match in DIALOGUE.finditer(analysis):
        exclude(*match.span(), 'explicit_dialogue')
    # Without a semantic parser, abstain on the rest of a reported-speech sentence.
    for match in REPORTED.finditer(analysis):
        tail = re.search(r'[.!؟?\n]', analysis[match.end():])
        end = match.end() + tail.start() if tail else len(text)
        exclude(match.start(), end, 'ambiguous_reported_speech')
    excluded.sort(key=lambda x: (x['start'], x['end'], x['reason']))

    def blocked(start, end):
        return any(start < s['end'] and end > s['start'] for s in excluded)

    # Paragraphs and explicit audience switches end the address comparison scope.
    cuts = {0, len(text)}
    cuts.update(m.end() for m in re.finditer(r'\n\s*\n', analysis))
    cuts.update(m.start() for m in AUDIENCE.finditer(analysis) if not blocked(*m.span()))
    for span in excluded:
        cuts.update((span['start'], span['end']))
    cuts = sorted(cuts)

    def scope(position):
        return sum(c <= position for c in cuts) - 1

    def signals(pattern, kind):
        found = []
        for match in pattern.finditer(analysis):
            if blocked(*match.span()):
                continue
            start, end = match.span()
            item = {'kind': kind, 'evidence': text[start:end], 'start': start,
                    'end': end, 'scope': scope(start)}
            if kind == 'address':
                item['value'] = 'shoma' if match.group('pronoun') == 'شما' else 'to'
            found.append(item)
        return found

    addresses = signals(ADDRESS, 'address')
    admin = signals(ADMIN, 'administrative')
    colloquial = signals(COLLOQUIAL, 'colloquial')
    findings = []

    def add(rule, evidence, reason, suggestion):
        findings.append({'rule_id': rule, 'reason': reason, 'suggestion': suggestion,
                         'attribution': 'requires_context_review',
                         'evidence': [{k: v for k, v in e.items() if k != 'scope'} for e in evidence]})

    for previous, current in zip(addresses, addresses[1:]):
        if previous['scope'] == current['scope'] and previous['value'] != current['value']:
            add('fa-address-shift', [previous, current],
                'در یک محدودهٔ روایت دو صورت متفاوت خطاب دیده شد؛ عمدی‌بودن تغییر را بررسی کنید.',
                'اگر مخاطب یکسان است، خطاب را یکدست کنید.')
    for item in addresses:
        if target_address != 'unspecified' and item['value'] != target_address:
            add('fa-target-address', [item], 'خطاب صریح با خطاب هدف متفاوت است.',
                'خطاب را با مخاطب و تنظیم انتخاب‌شده تطبیق دهید.')
    for a in admin:
        partner = next((c for c in colloquial if c['scope'] == a['scope']), None)
        if partner:
            add('fa-mixed-register', sorted([a, partner], key=lambda e: e['start']),
                'عبارت اداری و محاوره‌ای در یک بند دیده شد.',
                'تناسب این ترکیب با بافت را بررسی و در صورت نیاز عبارت‌ها را هماهنگ کنید.')
    mismatches = colloquial if target_tone == 'formal' else admin if target_tone in ('semi-formal', 'colloquial') else []
    for item in mismatches:
        add('fa-target-tone', [item], 'این عبارت با سیاست لحن هدف نیازمند تطبیق است.',
            'با توجه به مخاطب، عبارت را با لحن انتخاب‌شده هماهنگ کنید.')
    findings.sort(key=lambda f: (f['evidence'][0]['start'], f['rule_id']))
    sufficient = len(addresses) >= 2 or bool((target_address != 'unspecified' and addresses)
                      or (target_tone and (admin or colloquial)))
    assessment = 'findings_present' if findings else 'no_findings' if sufficient else 'insufficient_evidence'
    return {'target_tone': target_tone, 'target_address': target_address,
            'assessment': assessment, 'findings': findings, 'excluded_spans': excluded,
            'limitations': list(LIMITATIONS)}


def render_tone(report, out):
    labels = {'findings_present': 'نیازمند بررسی بافت', 'no_findings': 'در محدودهٔ قواعد، موردی پیدا نشد',
              'insufficient_evidence': 'شواهد ناکافی'}
    print('بررسی سازگاری لحن: ' + labels[report['assessment']], file=out)
    for finding in report['findings']:
        print('- ' + finding['reason'], file=out)
        for item in finding['evidence']:
            print(f"  [{item['start']}:{item['end']}] «{item['evidence']}»", file=out)
        print('  پیشنهاد: ' + finding['suggestion'], file=out)
    for limitation in report['limitations']:
        print('  محدودیت: ' + limitation, file=out)
