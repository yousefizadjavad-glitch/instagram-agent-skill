"""Conservative immutable spans in the original Unicode source."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from persian_review import quote_spans, BOUNDARY
from persian_dialogue import labelled_dialogue_spans


def protected_spans(text, protect=()):
    spans = []

    def add(start, end, reason):
        if start < end:
            spans.append(dict(start=start, end=end, text=text[start:end], reason=reason))

    patterns = {
        'url': r'https?://[^\s<>]+|www\.[^\s<>]+',
        'email': r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',
        'hashtag': r'#[\w\u200c]+',
        'mention': r'@[\w.]+',
        'number': r'[+−-]?\d+(?:[.,٫٬/:–-]\d+)*(?:[ \t]*(?:٪|%|تومان|ریال|دلار|یورو))?',
        'latin_or_code': r'[A-Za-z][A-Za-z0-9_.+/-]*(?:[ \t]+[A-Za-z0-9][A-Za-z0-9_.+/-]*)*',
        'dialogue': r'(?m)^[ \t]*(?:مشتری|پشتیبان|گوینده(?:ٔ? [۱۲12])?|کاربر|فروشنده)[ \t]*[:：][^\n]*',
        'code': r'```[\s\S]*?(?:```|\Z)|`[^`\n]*(?:`|$)',
    }
    for reason, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            add(*match.span(), reason)
    for start, end in labelled_dialogue_spans(text):
        add(start, end, 'dialogue')
    for start, end in quote_spans(text):
        add(start, end, 'quotation')
    for literal in protect:
        if not literal:
            raise ValueError('protected phrase must not be empty')
        for match in re.finditer(re.escape(literal), text):
            add(*match.span(), 'user_protected')
    # Explicit naming cues only: this is not general brand/name recognition.
    # Unknown names still require --protect. Stop at a clause delimiter; deliberately
    # overprotect surrounding words rather than guess where the name ends.
    naming = re.compile(r'(?<!' + BOUNDARY + r')(?P<cue>برند|نام تجاری|نام محصول|نام مجموعه|عنوان(?: (?:کتاب|اثر|فیلم|نمایشگاه))?)(?P<separator>[ \t]*[:：][ \t]*|[ \t]+)(?P<content>[^.!؟?؛\r\n]+)')
    for match in naming.finditer(text):
        cue = match.group('cue')
        if cue.startswith('عنوان'):
            # "به عنوان نمونه" is not a title introduction. Bare "عنوان" needs
            # a colon or a quoted title; no generic title/name inference.
            if re.search(r'(?<!' + BOUNDARY + r')(?:به|تحت)[ \t]+\Z', text[:match.start()]):
                continue
            if cue == 'عنوان' and not (':' in match.group('separator') or '：' in match.group('separator')
                                       or match.group('content').lstrip().startswith(('«', '“', '"'))):
                continue
        if not any(s['reason'] == 'user_protected' and s['start'] <= match.start()
                   and s['end'] > match.end('cue') + 1 for s in spans):
            add(*match.span(), 'suspected_name_context')
    # An explicit statement about a name's orthography is a safety cue, not NER.
    # Guard the whole sentence rather than guess the exact name boundaries.
    for sentence in re.finditer(r'[^.!؟?\r\n]+', text):
        part = sentence.group()
        if (re.search(r'(?<!' + BOUNDARY + r')(?:فاصله(?:ٔ|‌ی|ی)?|نگارش|املای)(?!' + BOUNDARY + r')', part)
                and re.search(r'(?<!' + BOUNDARY + r')(?:این نام|این عنوان|نام محصول|نام مجموعه)(?!' + BOUNDARY + r')', part)
                and re.search(r'عمدی است|هویت بصری|عیناً|حفظ', part)):
            add(*sentence.span(), 'suspected_name_context')
    # Lock sensitive clauses, rather than assuming unchanged keywords preserve meaning.
    sensitive = re.compile(r'(?<!' + BOUNDARY + r')(?:نیست|نیستند|نه|بدون|اگر|مگر|فقط|حداقل|حداکثر|شاید|احتمالاً|حتماً|تضمینی|قطعی|باید|شما|تو|ممکن است|به شرط|برخی|همه|تا|نمی[\w\u200c]*|نکن[\w\u200c]*)(?!' + BOUNDARY + r')')
    for clause in re.finditer(r'[^.!؟?\n]+', text):
        if sensitive.search(clause.group()):
            add(*clause.span(), 'sensitive_clause')
        if re.search(r'(?<!' + BOUNDARY + r')(?:گفت|نوشت|پرسید)(?!' + BOUNDARY + r')', clause.group()):
            add(*clause.span(), 'reported_speech')
    # Alignment, lists, tabs and unknown format controls are not plain prose.
    for line in re.finditer(r'[^\n]+', text):
        value = line.group()
        if (re.match(r'[ \t]|[-*•>#]', value) or '\t' in value or '|' in value
                or re.search(r'[\u200b\u200d\u202a-\u202e\u2066-\u2069\ufeff]', value)):
            add(*line.span(), 'ambiguous_layout')
    return sorted(spans, key=lambda s: (s['start'], s['end'], s['reason']))


def overlaps(start, end, spans):
    return [s for s in spans if start < s['end'] and end > s['start']]
