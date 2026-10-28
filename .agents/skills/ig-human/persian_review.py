"""Conservative Persian style review; no authorship or naturalness scoring.

Offsets are zero-based Python Unicode code-point indexes into unchanged input;
end is exclusive. Rules are editorial prompts, not validated classifications.
"""
import json
from pathlib import Path
import re
import unicodedata

from text_core import words
from persian_review_context import clear_exception

RULES = Path(__file__).with_name('fa_style_rules.json')
NOTICE = 'این بازبینی پیشنهاد ویرایشی است؛ دربارهٔ طبیعی‌بودن متن یا هویت نویسنده داوری نمی‌کند. نبود یافته نیز تأیید کیفیت متن نیست.'
BOUNDARY = r'[\w\u200c\u064b-\u065f\u0670]'


def load_rules(path=RULES):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)['rules']


def quote_spans(text):
    """Track nested guillemets/curly/ASCII quotes, including unclosed quotes.

    Straight single quotes are delimiters only outside words (don't isn't a
    quote). Any overlap is conservatively marked for contextual review.
    """
    pairs = {'«': '»', '“': '”', '‘': '’', '"': '"', "'": "'"}
    stack, spans = [], []
    for i, char in enumerate(text):
        if char in "'’" and i and i + 1 < len(text) and text[i-1].isalnum() and text[i+1].isalnum():
            continue
        if stack and char == stack[-1][1]:
            start, _ = stack.pop()
            spans.append((start, i + 1))
        elif char in pairs:
            stack.append((i, pairs[char]))
    spans.extend((start, len(text)) for start, _ in stack)
    return spans


def review(text, rules=None):
    quotes = quote_spans(text)
    findings = []
    # Same-length Arabic letter variants for matching only. Source is untouched.
    analysis = text.translate(str.maketrans({'ي': 'ی', 'ك': 'ک'}))
    for rule in load_rules() if rules is None else rules:
        pattern = re.compile(r'(?<!' + BOUNDARY + r')(?:' + rule['pattern'] + r')(?!' + BOUNDARY + r')')
        for match in pattern.finditer(analysis):
            start, end = match.span()
            if rule['warning_type'] == 'obvious_repetition':
                if not any('ARABIC' in unicodedata.name(c, '') for c in match.group('word')):
                    continue
            if clear_exception(rule['id'], analysis, match, quotes):
                continue
            quoted = any(start < b and end > a for a, b in quotes)
            findings.append({
                'rule_id': rule['id'], 'warning_type': rule['warning_type'],
                'evidence': text[start:end], 'start': start, 'end': end,
                'reason': rule['reason'], 'suggestion': rule['suggestion'],
                'exceptions': rule['exceptions'], 'tones': rule['tones'],
                'quoted': quoted,
                'attribution': 'requires_quote_review' if quoted else 'requires_context_review',
            })
    findings.sort(key=lambda f: (f['start'], f['end'], f['rule_id']))
    return {'language': 'fa', 'mode': 'style_review', 'text': text,
            'word_count': len(words(text)), 'notice': NOTICE, 'findings': findings}


def render(report, out, label=None):
    print('بازبینی توصیفی فارسی' + (f' — {label}' if label else ''), file=out)
    print(report['notice'], file=out)
    if not report['findings']:
        print('در محدودهٔ قواعد اولیه، موردی برای بررسی پیدا نشد.', file=out)
    for finding in report['findings']:
        status = 'نیازمند بررسی نقل‌قول' if finding['quoted'] else 'نیازمند بررسی بافت'
        print(f"- [{finding['start']}:{finding['end']}] «{finding['evidence']}» ({status})", file=out)
        print('  دلیل: ' + finding['reason'], file=out)
        print('  پیشنهاد: ' + finding['suggestion'], file=out)
        print('  استثناها: ' + '؛ '.join(finding['exceptions']), file=out)
