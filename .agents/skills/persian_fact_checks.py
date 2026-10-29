"""Bounded explicit fact comparison, not truth checking or entity inference."""
import hashlib
import re
from decimal import Decimal

DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
NUMBER = r'[0-9۰-۹٠-٩]+(?:[,٬][0-9۰-۹٠-٩]{3})*(?:[.٫][0-9۰-۹٠-٩]+)?'
PATTERNS = {
    'price': re.compile(r'(?<![\w.,٬٫])(?P<value>'+NUMBER+r')\s*(?P<unit>تومان|ریال)(?!\w)'),
    'date': re.compile(r'(?<!\w)(?P<value>[0-9۰-۹٠-٩]{4}[/\-][0-9۰-۹٠-٩]{1,2}[/\-][0-9۰-۹٠-٩]{1,2})(?![\w/\-])'),
    'product_code': re.compile(r'(?:کد محصول|شناسهٔ محصول|شناسه محصول)\s*[:：]\s*(?P<value>[A-Za-z0-9۰-۹٠-٩]+(?:[-_][A-Za-z0-9۰-۹٠-٩]+)*)(?![\w-])'),
    'name': re.compile(r'(?:برند|نام محصول)\s*[:：]\s*(?P<value>[^\n؛;،,.!?؟]+)'),
}
LIMITATIONS = [
    'مقایسه محدود عبارات صریح است؛ تأیید کلی صحت یا حقیقت‌سنجی انجام نمی‌شود.',
    'نام فقط با نشانگر برند:/نام محصول: و معرفی عین نام در protected_terms بررسی می‌شود؛ نام حدس زده نمی‌شود.',
    'انتساب چندمحصولی، چندقیمتی، نفی، نقل‌قول و بافت حساس نیازمند انسان است.',
    'تاریخ فقط شکل عددی سال/ماه/روز است؛ تقویم‌ها تبدیل و تاریخ اعتبارسنجی تقویمی نمی‌شود.',
    'تومان و ریال تبدیل نمی‌شوند؛ اطلاعات غایب تناقض محسوب نمی‌شوند.',
]


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def extract(text, protected):
    result = []
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if any(a.start() <= match.start() < a.end() for a in re.finditer(r'https?://\S+', text)):
                continue
            value = match.group('value').strip()
            if kind == 'name' and not any(value == term for term in protected):
                # Unknown explicit names remain evidence, but cannot establish a baseline.
                known = False
            else:
                known = True
            normalized = value.translate(DIGITS)
            if kind == 'price':
                normalized = normalized.replace(',', '').replace('٬', '').replace('٫', '.')
                normalized = str(Decimal(normalized).normalize())
            if kind == 'date':
                normalized = '-'.join(str(int(part)) for part in re.split(r'[/\-]', normalized))
            if kind == 'name':
                normalized = value  # Explicit names must not be rewritten or whitespace-normalized.
            result.append(dict(kind=kind, value=value, normalized=normalized,
                unit=match.groupdict().get('unit'), known=known,
                start=match.start(), end=match.end(), before=text[match.start():match.end()]))
    return sorted(result, key=lambda item:item['start'])


def check_facts(verified_facts, protected_terms, sections, request_hash):
    """sections contain exact text, section_id and source_hash; never mutate them."""
    expected = []
    for index, text in enumerate(verified_facts):
        for item in extract(text, protected_terms):
            item.update(section_id=f'brief.verified_facts.{index}', source_hash=sha(text))
            expected.append(item)
    report = dict(source_hash=request_hash, section_id='workflow', fact_checks=[], mismatches=[],
                  ambiguous=[], limitations=list(LIMITATIONS), status='not_checked')
    identities = {x['normalized'] for x in expected if x['kind']=='name'}
    all_actual = []
    for section in sections:
        for item in extract(section['source_text'], protected_terms):
            item.update(section_id=section['section_id'], source_hash=section['source_hash'])
            all_actual.append(item)
    identities.update(x['normalized'] for x in all_actual if x['kind']=='name')
    # More than one product label anywhere precludes implicit single-product attribution.
    multi_product = len(identities)>1
    for section in sections:
        text = section['source_text']
        actual = [x for x in all_actual if x['section_id']==section['section_id']]
        for kind in PATTERNS:
            baseline = [x for x in expected if x['kind']==kind and (kind!='name' or x['known'])]
            observed = [x for x in actual if x['kind']==kind]
            if not baseline or not observed:
                continue  # Absence, and unanchored new information, are not contradictions.
            reason = None
            if len(baseline)!=1 or len(observed)!=1:
                reason='multiple_values_or_products'
            elif kind!='name' and multi_product:
                reason='multiple_values_or_products'
            elif re.search(r'نیست|نبود|نه\b|اگر|شاید|احتمال|قبلی|جدید|تخفیف|از\s+.+\s+تا|[«»“”"]', text) or any(
                    re.search(r'نیست|نبود|اگر|شاید|احتمال|قبلی|جدید|تخفیف|[«»“”"]', fact) for fact in verified_facts):
                reason='context_requires_review'
            a, b = baseline[0], observed[0]
            if not reason and kind=='price':
                def clear_price_role(source, record):
                    prefix = re.split(r'[؛;\n.!؟?]', source[:record['start']])[-1].strip()
                    return prefix in ('', 'قیمت', 'قیمت:', 'قیمت :', 'قیمت：')
                if not clear_price_role(text, b) or not all(clear_price_role(verified_facts[int(x['section_id'].rsplit('.',1)[1])], x) for x in baseline):
                    reason='price_attribution_requires_review'
            if not reason and kind=='date' and (re.search(r'تاریخ\s+(?:تحویل|تولید|انقضا|سفارش|پرداخت)', text) or any(re.search(r'تاریخ\s+(?:تحویل|تولید|انقضا|سفارش|پرداخت)', fact) for fact in verified_facts)):
                reason='date_role_requires_review'
            if not reason and kind=='price' and a['unit']!=b['unit']:
                reason='different_currency_units'
            item = dict(kind=kind, section_id=section['section_id'], source_hash=section['source_hash'],
                        expected=baseline, observed=observed, requires_human_review=True)
            if reason:
                item.update(status='ambiguous', reason=reason)
                report['ambiguous'].append(item)
            elif a['normalized']!=b['normalized']:
                item.update(status='mismatch', reason='explicit_value_conflict')
                report['mismatches'].append(item)
            else:
                item.update(status='matched_explicit_value', reason='literal_value_match_only')
            report['fact_checks'].append(item)
    report['status'] = 'needs_review' if report['mismatches'] or report['ambiguous'] else 'limited_comparison' if report['fact_checks'] else 'not_checked'
    return report
