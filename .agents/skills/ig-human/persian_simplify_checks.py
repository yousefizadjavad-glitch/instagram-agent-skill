"""Separate, conservative validation for language suggestions; no application."""
import re
from persian_protection import overlaps
from persian_review import BOUNDARY

# Additional barriers belong only to the new path; version-one protection is unchanged.
BARRIER = re.compile(r'(?<!' + BOUNDARY + r')(?:نشود|نشده|نشد|ندارد|نبود|نخواهد|نتوان[\w‌]*|نیستند|قانونی|مقررات|تبصره|صرفاً|در صورت|مشروط|منوط|احتمال|شاید|ممکن|نفی|نه|نیست|نمی[\w‌]*|اگر|مگر|تضمین[\w‌]*|قطعاً|حتماً|باید|شما|تو|فقط|تا|قرارداد|حقوقی|قانون|تعهد|مسترد|مدیر|کنایه|چه خدمات سریعی)(?!' + BOUNDARY + r')')


# Finite common negative families, not a parser or a complete scope detector.
NEGATION = re.compile(r'(?<!' + BOUNDARY + r')(?:'
    r'ندار(?:م|ی|د|یم|ید|ند)|نیست(?:م|ی|یم|ید|ند)?|'
    r'نبود(?:م|ی|یم|ید|ند)?|نشد(?:م|ی|یم|ید|ند)?|نشو(?:م|ی|د|یم|ید|ند)|'
    r'نخواه(?:م|ی|د|یم|ید|ند)|نکن(?:م|ی|د|یم|ید|ند)?|'
    r'نداشته(?:[ ‌](?:ام|ای|ایم|اید|اند))?|'
    r'نتوان(?:م|ی|د|یم|ید|ند|ست(?:م|ی|یم|ید|ند)?)|'
    r'نمی[ ‌]?(?:دان|توان|خواه|کن|شو|شد|رو)(?:م|ی|د|یم|ید|ند)|'
    r'هرگز|هیچ)(?!' + BOUNDARY + r')')


# A separate language-only guard: do not expand mechanical version-one policy.
PROHIBITION = re.compile(r'(?<!' + BOUNDARY + r')(?:نباید|نکنید|ممنوع[ \t]+است|مجاز[ \t]+نیست)(?!' + BOUNDARY + r')')


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
    if sentence is not None and PROHIBITION.search(sentence):
        return 'prohibition_requires_review'
    if sentence is not None and NEGATION.search(sentence):
        return 'negation_requires_review'
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
