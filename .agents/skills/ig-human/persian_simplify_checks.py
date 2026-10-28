"""Separate, conservative validation for language suggestions; no application."""
import re
from persian_protection import overlaps
from persian_review import BOUNDARY

# Additional barriers belong only to the new path; version-one protection is unchanged.
BARRIER = re.compile(r'(?<!' + BOUNDARY + r')(?:نشود|نشده|نشد|ندارد|نبود|نخواهد|نتوان[\w‌]*|نیستند|قانونی|مقررات|تبصره|صرفاً|در صورت|مشروط|منوط|احتمال|شاید|ممکن|نفی|نه|نیست|نمی[\w‌]*|اگر|مگر|تضمین[\w‌]*|قطعاً|حتماً|باید|شما|تو|فقط|تا|قرارداد|حقوقی|قانون|تعهد|مسترد|مدیر|کنایه|چه خدمات سریعی)(?!' + BOUNDARY + r')')


def sentence_spans(text):
    # Ignore periods within URLs, decimals and Latin identifiers.
    protected = []
    for m in re.finditer(r'https?://\S+|www\.\S+|[A-Za-z0-9][A-Za-z0-9_.]*|\d+[.٫]\d+', text):
        protected.append(m.span())
    start = 0
    for m in re.finditer(r'[.!؟?\n]', text):
        if any(a <= m.start() < b for a, b in protected):
            continue
        if start < m.start():
            yield start, m.start()
        start = m.end()
    if start < len(text):
        yield start, len(text)


def validate(text, candidate, spans, rule):
    a, b = candidate['start'], candidate['end']
    if not 0 <= a < b <= len(text) or text[a:b] != candidate['before']:
        return 'invalid_source_span'
    if overlaps(a, b, spans):
        return 'protected_span'
    sentence = next((text[s:e] for s, e in sentence_spans(text) if s <= a and b <= e), None)
    if sentence is None or BARRIER.search(sentence):
        return 'sensitive_or_ambiguous_context'
    if rule['id'] == 'fa-request' and sentence.strip() != candidate['before']:
        return 'incomplete_request_context'
    # Unknown heavy clauses and apparent irony never authorize a patch.
    if len(sentence.split()) > 35 or re.search(r'مقتضی است|به استحضار|می[‌ ]باشد|انجام می[‌ ]پذیرد|به عمل|صورت می[‌ ]گیرد|چه .+؛', sentence):
        return 'human_review_required'
    match = re.compile(r'(?<!' + BOUNDARY + r')(?:' + rule['pattern'] + r')(?!' + BOUNDARY + r')').match(text, a)
    if not match or match.end() != b:
        return 'rule_mismatch'
    expected = rule['replacement'].format(**match.groupdict())
    if candidate['replacement'] != expected or expected == candidate['before']:
        return 'invalid_replacement'
    if not candidate.get('requires_confirmation'):
        return 'confirmation_required'
    return None
