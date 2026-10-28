"""Narrow contextual exceptions for Persian review, never a semantic verdict."""
import re

BOUNDARY = r'[\w\u200c\u064b-\u065f\u0670]'
UNCERTAIN = re.compile(r'(?<!' + BOUNDARY + r')(?:اگر|مگر|شاید|احتمالاً|ظاهراً|گویا|انگار|آیا|اینکه|ممکن|نه|نمی[\w‌]*|اما|ولی|بلکه)(?!' + BOUNDARY + r')')


def clause(text, start, end):
    """A conservative local clause; punctuation is not linguistic parsing."""
    left = re.search(r'[^.!؟?؛\n]*$', text[:start]).group()
    right = re.match(r'[^.!؟?؛\n]*', text[end:]).group()
    return left, right, text[end + len(right):end + len(right) + 1]


def same_quote_scope(start, end, other_start, other_end, quotes):
    first = {(a, b) for a, b in quotes if start < b and end > a}
    second = {(a, b) for a, b in quotes if other_start < b and other_end > a}
    return first == second


def clear_negated_claim(text, match, quotes):
    # Only the matched guarantee itself immediately followed by a negative copula.
    if not re.fullmatch(r'(?:موفقیت|نتیجه)(?:[‌ ]ی)? (?:صد[‌ ]?در[‌ ]?صد |۱۰۰٪ |100% |١٠٠٪ )?تضمینی', match.group()):
        return False
    neg = re.match(r'[ \t]+(?:نیست|نیستند|نبود|نبوده است)(?!' + BOUNDARY + r')', text[match.end():])
    if not neg:
        return False
    end = match.end() + neg.end()
    if not same_quote_scope(match.start(), match.end(), match.end() + neg.start(), end, quotes):
        return False
    before, after, punctuation = clause(text, match.start(), end)
    if punctuation in ('؟', '?') or UNCERTAIN.search(before + ' ' + after):
        return False
    # Extra predicates can reverse or qualify the negation (e.g. درست نیست).
    return not after.strip(" \t»”’\"'")


# A question mark alone does not establish relevance. Only these complete,
# immediately adjacent preference/comparison questions support an opinion CTA.
QUESTION = re.compile(
    r'(?:کدام|کدوم) (?:رنگ|مدل|طرح|گزینه|کتاب|عکس)'
    r'(?:(?: را| رو)? (?:ترجیح می[‌ ]دهید|ترجیح می[‌ ]دین|ترجیح می[‌ ]دی|انتخاب می[‌ ]کنید|انتخاب می[‌ ]کنی)'
    r'|(?: برای (?:میز کوچک|اتاق کوچک|خانه|آشپزخانه))? (?:بهتر|مناسب[‌ ]تر) است)')
OPINION_CTA = re.compile(r'نظرت(?:ان|ون) (?:را |رو )?(?:بنویسید|بنویسین|بگید|بگین)')


def related_opinion_cta(text, match, quotes):
    if not OPINION_CTA.fullmatch(match.group()):
        return False
    prefix = text[:match.start()]
    # At most one line break and no intervening sentence, link or campaign text.
    suffix = re.search(r'[؟?]([ \t]*(?:\r?\n[ \t]*)?)\Z', prefix)
    if not suffix:
        return False
    question_end = suffix.start()
    previous = list(re.finditer(r'[.!؟?؛\n]', text[:question_end]))
    start = previous[-1].end() if previous else 0
    segment = text[start:question_end]
    leading = len(segment) - len(segment.lstrip(' \t'))
    question = segment.strip(' \t')
    start += leading
    if not QUESTION.fullmatch(question):
        return False
    _, after, _ = clause(text, match.start(), match.end())
    if after.strip(" \t»”’\"'"):
        return False
    return same_quote_scope(start, question_end, match.start(), match.end(), quotes)


def clear_emotional_emphasis(text, match, quotes):
    # No general exemption for repetitions: exactly two intensifiers plus a
    # small first-person emotional phrase, not triple repetitions or noun loops.
    if not re.fullmatch(r'خیلی +خیلی', match.group()):
        return False
    emotion = re.match(r' +(?:خوشحالم|خوشحالیم|دلتنگم|ممنونم|متشکرم)(?!' + BOUNDARY + r')', text[match.end():])
    if not emotion:
        return False
    end = match.end() + emotion.end()
    if not same_quote_scope(match.start(), match.end(), match.end(), end, quotes):
        return False
    before, after, punctuation = clause(text, match.start(), end)
    if punctuation in ('؟', '?') or UNCERTAIN.search(before + ' ' + after):
        return False
    # Negated emotion is outside this deliberately narrow exception.
    if re.search(r'(?<!' + BOUNDARY + r')(?:نیست|نبود|نیستم|نبودم)(?!' + BOUNDARY + r')', after):
        return False
    return not after.strip(" \t»”’\"'")


def clear_exception(rule_id, text, match, quotes):
    handlers = {'fa-absolute-promise': clear_negated_claim,
                'fa-generic-engagement': related_opinion_cta,
                'fa-obvious-repetition': clear_emotional_emphasis}
    handler = handlers.get(rule_id)
    return bool(handler and handler(text, match, quotes))
