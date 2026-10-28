"""Offline Persian mechanical suggestions. Source is never rewritten."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from persian_protection import protected_spans
from persian_rewrite_checks import validate, mark_conflicts
from persian_review import BOUNDARY

RULES = Path(__file__).with_name('persian_rewrite_rules.json')
LIMITATIONS = [
    'این ابزار فقط پیشنهاد می‌دهد؛ حفظ کامل معنا یا طبیعی‌بودن تضمین نمی‌شود.',
    'نام‌های فارسی ناشناخته را با --protect مشخص کنید؛ شناسایی جامع نام و اطلاعات حساس انجام نمی‌شود.',
    'نفی، شرط، قطعیت و خطاب با واژگان محدود محافظت می‌شوند؛ ابهام زبانی و چیدمان نیازمند بررسی انسان است.',
    'این مرحله فقط فاصله و چند ترکیب نیم‌فاصله را بررسی می‌کند؛ لحن و ساختار را تغییر نمی‌دهد.',
]


def suggest(text, protect=()):
    protect = list(protect)
    spans = protected_spans(text, protect)
    rules = json.loads(RULES.read_text(encoding='utf-8'))['rules']
    candidates = []
    for rule in rules:
        if rule['kind'] == 'space':
            # Persian letters on both sides; never collapse newlines or indentation.
            pattern = r'(?<=[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc]) {2,}(?=[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc])'
        else:
            pattern = r'(?<!' + BOUNDARY + r')(?:' + '|'.join(re.escape(f) for f in rule['forms']) + r')(?!' + BOUNDARY + r')'
        for match in re.finditer(pattern, text):
            before = match.group()
            candidates.append(dict(rule_id=rule['id'], start=match.start(), end=match.end(),
                before=before, replacement=' ' if rule['kind'] == 'space' else before.replace(' ', '\u200c'),
                category='mechanical', reason=rule['reason'], requires_confirmation=True))
    suggestions, abstentions = [], []
    for candidate in sorted(candidates, key=lambda c: (c['start'], c['end'], c['rule_id'])):
        error = validate(text, candidate, spans)
        if error:
            abstentions.append(dict(start=candidate['start'], end=candidate['end'],
                before=candidate['before'], rule_id=candidate['rule_id'], reason=error))
        else:
            candidate['id'] = 's' + str(len(suggestions) + 1)
            candidate['checks'] = {'protected_spans': 'passed', 'semantic_review': 'required'}
            suggestions.append(candidate)
    mark_conflicts(suggestions)
    return dict(schema_version=1, language='fa', mode='rewrite_suggestions', engine='offline_rules',
        source_text=text, source_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
        options={'protect': protect}, suggestions=suggestions, protected_spans=spans,
        abstentions=abstentions, limitations=list(LIMITATIONS),
        status='suggestions_available' if suggestions else 'insufficient_context' if abstentions else 'no_suggestions')


def main():
    parser = argparse.ArgumentParser(description='پیشنهاد آفلاین اصلاح محدود فارسی؛ بدون تغییر فایل')
    parser.add_argument('input', nargs='?', default='-')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--protect', action='append', default=[])
    args = parser.parse_args()
    if any(not value for value in args.protect):
        parser.error('--protect must not be empty')
    try:
        # Preserve CRLF: offsets and hash always refer to exactly decoded UTF-8 bytes.
        raw = sys.stdin.buffer.read() if args.input == '-' else Path(args.input).read_bytes()
        report = suggest(raw.decode('utf-8'), args.protect)
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('پیشنهاد اصلاح فارسی؛ هیچ تغییری اعمال نشده است.')
        for s in report['suggestions']:
            print(f"[{s['start']}:{s['end']}] {s['before']!r} → {s['replacement']!r}")
            print(s['reason'])
        if not report['suggestions']:
            print('در محدودهٔ قواعد، پیشنهادی ارائه نشد.')
        for limitation in report['limitations']:
            print(limitation)
    return 0


if __name__ == '__main__':
    sys.exit(main())
