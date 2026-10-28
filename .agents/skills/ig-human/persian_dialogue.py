"""Structural dialogue hints, not person-name recognition or speaker inference."""
import re

LABELLED_LINE = re.compile(r'(?m)^[ \t]*(?P<label>[^\W\d_]+(?:[ ‌][^\W\d_]+)?)[ \t]*[:：](?P<body>[^\r\n]+)')
DIALOGUE_CUE = re.compile(r'(?<![\w‌])(?:دیالوگ|گفت[‌ ]وگو|گفتگو|نمایشنامه)(?![\w‌])')
NOT_DIALOGUE = re.compile(r'(?:دیالوگ|گفت[‌ ]وگو|گفتگو|نمایشنامه)[ \t]+(?:نیست|نبود)(?![\w‌])')
HEADINGS = {'نکته', 'هشدار', 'توجه', 'مرحله', 'بخش', 'فصل', 'سؤال', 'پاسخ', 'عنوان',
            'برند', 'نام', 'مثال', 'خلاصه', 'راهنما', 'نتیجه', 'امروز', 'فردا'}
# These already have legacy handling; avoid duplicate protected/excluded spans.
LEGACY_ROLES = {'مشتری', 'پشتیبان', 'گوینده', 'کاربر', 'فروشنده'}


def labelled_dialogue_spans(text):
    """Protect adjacent distinct short labels only with an explicit nearby cue.

    Arbitrary headings or bare labels are not enough. Unknown/unlabelled speech
    remains ambiguous and may need human review.
    """
    candidates = []
    for match in LABELLED_LINE.finditer(text):
        label = match.group('label')
        if (not match.group('body').strip() or len(label) > 24 or not re.search(r'[\u0621-\u06cc]', label)
                or label.split()[0] in HEADINGS or label in LEGACY_ROLES):
            continue
        candidates.append(match)
    groups = []
    for match in candidates:
        if groups and not text[groups[-1][-1].end():match.start()].strip() and text[groups[-1][-1].end():match.start()].count('\n') <= 2:
            groups[-1].append(match)
        else:
            groups.append([match])
    spans = []
    for group in groups:
        if len({m.group('label') for m in group}) < 2:
            continue
        context = text[max(0, group[0].start()-100):min(len(text), group[-1].end()+100)]
        if not DIALOGUE_CUE.search(context) or NOT_DIALOGUE.search(context):
            continue
        spans.extend(m.span() for m in group)
    return spans
