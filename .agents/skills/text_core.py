"""Shared Unicode text primitives. No language detection or scoring policy.

ZWNJ validity is a conservative Arabic-script context check, not a proof of
Persian spelling. Other format characters remain subject to existing cleanup.
Digit normalization is analysis-only: callers retain the user's source text.
"""
import re
import unicodedata

ZWNJ = '\u200c'
SENT_RE = re.compile(r'[^.!?؟\n]+[.!?؟]*')


def normalize_numbers(text):
    text = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    text = re.sub(r'(?<=\d)٬(?=\d)', ',', text)
    text = re.sub(r'(?<=\d)٫(?=\d)', '.', text)
    return text.replace('٪', '%')


def _arabic_letter(c):
    return unicodedata.category(c).startswith('L') and 'ARABIC' in unicodedata.name(c, '')


def valid_zwnj(text, index):
    if text[index] != ZWNJ:
        return False
    left, right = index - 1, index + 1
    while left >= 0 and unicodedata.category(text[left]).startswith('M'):
        left -= 1
    while right < len(text) and unicodedata.category(text[right]).startswith('M'):
        right += 1
    return left >= 0 and right < len(text) and _arabic_letter(text[left]) and _arabic_letter(text[right])


def suspicious_format(text, index):
    return unicodedata.category(text[index]) == 'Cf' and not valid_zwnj(text, index)


def words(text, *, detector=False):
    """Count ZWNJ compounds as one token; retain each tool's English policy.

    The detector historically counts letter words, excluding numbers, while
    Reel tools count numbers and currency too. Keep that distinction explicit.
    """
    text = normalize_numbers(text)
    text = ''.join(' ' if c == ZWNJ and not valid_zwnj(text, i) else c
                   for i, c in enumerate(text))
    if not detector:
        text = re.sub(r'(?<=\d),(?=\d)', '', text)
    tokens, current = [], []
    symbols = "'" if detector else "$%'’-"
    for i, char in enumerate(text):
        category = unicodedata.category(char)
        keep = (category.startswith('L') or
                (category.startswith('N') and not detector) or
                (category.startswith('M') and bool(current)) or
                char in symbols or
                (char == ZWNJ and valid_zwnj(text, i)))
        if keep:
            current.append(char)
        elif current:
            tokens.append(''.join(current))
            current = []
    if current:
        tokens.append(''.join(current))
    return tokens
