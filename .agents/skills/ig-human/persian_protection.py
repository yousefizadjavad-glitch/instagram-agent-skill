"""Conservative immutable spans in the original Unicode source."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from persian_review import quote_spans, BOUNDARY


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
    for start, end in quote_spans(text):
        add(start, end, 'quotation')
    for literal in protect:
        if not literal:
            raise ValueError('protected phrase must not be empty')
        for match in re.finditer(re.escape(literal), text):
            add(*match.span(), 'user_protected')
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
