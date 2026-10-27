"""Phase two review and legacy CLI contracts; stdlib only, no network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / '.agents/skills'
HUMAN = CORE / 'ig-human'
sys.path[:0] = [str(CORE), str(HUMAN)]
from persian_review import load_rules, review


def cli(*args, text='', original=False):
    script = (ROOT / 'skills/ig-human' if original else HUMAN) / 'detect.py'
    return subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                          input=text, text=True, capture_output=True, cwd='/tmp')


class PersianReviewTests(unittest.TestCase):
    def test_formal(self):
        report = review('بدین‌وسیله به استحضار می‌رساند جلسه فردا برگزار می‌شود.')
        self.assertEqual(report['findings'][0]['warning_type'], 'heavy_administrative')

    def test_colloquial_clean(self):
        self.assertEqual(review('امروز رفتم بازار؛ این مدل رو با ۳۰۰ هزار تومن خریدم. تو کدوم مدل رو امتحان کردی؟')['findings'], [])

    def test_advertising_categories(self):
        report = review('در دنیای امروز، تجربه‌ای بی‌نظیر با موفقیت صددرصد تضمینی. نظرتون رو بگید.')
        self.assertEqual([f['warning_type'] for f in report['findings']],
                         ['cliche_opening', 'vague_promotion', 'absolute_promise', 'generic_engagement'])

    def test_repetition(self):
        report = review('این خیلی خیلی خیلی خوبه؛ خانه‌ها خانه‌ها زیبا هستند.')
        self.assertEqual([f['evidence'] for f in report['findings']], ['خیلی خیلی خیلی', 'خانه‌ها خانه‌ها'])

    def test_english_not_reviewed_as_persian(self):
        self.assertEqual(review('Unlock a seamless experience. very very good.')['findings'], [])

    def test_mixed(self):
        report = review('برای Reel تجربه‌ای بی‌نظیر بساز؛ Save this post!')
        self.assertEqual([f['evidence'] for f in report['findings']], ['تجربه‌ای بی‌نظیر'])

    def test_quotes_and_unquoted(self):
        for left, right in [('«', '»'), ('“', '”'), ('"', '"'), ("'", "'"), ('‘', '’')]:
            with self.subTest(left=left):
                findings = review(f'او گفت {left}کیفیت بی‌نظیر{right}؛ سپس نوشت کیفیت بی‌نظیر.')['findings']
                self.assertEqual([f['quoted'] for f in findings], [True, False])
                self.assertEqual(findings[0]['attribution'], 'requires_quote_review')

    def test_nested_and_unclosed_quotes(self):
        for text in ['«او گفت “کیفیت بی‌نظیر” و رفت»', 'او گفت «کیفیت بی‌نظیر', '«کیفیت بی‌نظیر» «کیفیت بی‌نظیر»']:
            self.assertTrue(all(f['quoted'] for f in review(text)['findings']))

    def test_apostrophe_is_not_quote(self):
        self.assertFalse(review("don't say کیفیت بی‌نظیر")['findings'][0]['quoted'])

    def test_source_and_offsets(self):
        text = '😀\nمی‌خواهم مُحتوا بسازم؛ کیفیت بی‌نظیر، كيفيت بي‌نظير. ۳٫۵٪'
        report = review(text)
        self.assertEqual(report['text'], text)
        self.assertEqual(len(report['findings']), 2)
        for finding in report['findings']:
            self.assertEqual(text[finding['start']:finding['end']], finding['evidence'])
            self.assertTrue(finding['reason'])
            self.assertTrue(finding['suggestion'])

    def test_word_boundaries(self):
        self.assertEqual(review('نامقتضی است؛ کیفیت بی‌نظیرتر')['findings'], [])

    def test_empty_and_short(self):
        for text in ['', '؟', 'سلام', 'می‌روم؟ نمی‌روم؟ چرا؟']:
            self.assertEqual(review(text)['findings'], [])

    def test_no_scores_or_authorship(self):
        report = review('کیفیت بی‌نظیر')
        self.assertEqual(set(report), {'language', 'mode', 'text', 'word_count', 'notice', 'findings'})
        self.assertFalse({'human_score', 'verdict', 'score', 'author'} & set(report['findings'][0]))

    def test_context_exceptions_are_visible(self):
        for text in ['این موفقیت تضمینی نیست.', 'آیا لایک کنید و به اشتراک بگذارید درخواست خوبی است؟', 'در نامهٔ اداری نوشت: مقتضی است']:
            finding = review(text)['findings'][0]
            self.assertTrue(finding['exceptions'])
            self.assertEqual(finding['attribution'], 'requires_context_review')

    def test_rule_schema_and_scope(self):
        rules = load_rules()
        self.assertEqual(len({r['id'] for r in rules}), len(rules))
        self.assertEqual({r['warning_type'] for r in rules}, {'cliche_opening', 'vague_promotion', 'absolute_promise', 'generic_engagement', 'heavy_administrative', 'obvious_repetition'})
        for rule in rules:
            self.assertEqual(set(rule), {'id', 'pattern', 'warning_type', 'reason', 'exceptions', 'tones', 'suggestion'})
            self.assertTrue(all(rule.values()))

    def test_fa_stdin_json_and_text(self):
        text = 'می‌خواهم کیفیت بی‌نظیر را بررسی کنم.'
        result = cli('-', '--lang', 'fa', '--json', text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['text'], text)
        rendered = cli('-', '--lang', 'fa', text=text)
        self.assertEqual(rendered.returncode, 0)
        self.assertIn('پیشنهاد:', rendered.stdout)
        self.assertIn('کیفیت بی‌نظیر', rendered.stdout)
        self.assertNotIn('HUMAN SCORE', rendered.stdout)

    def test_fa_files_compare_and_custom_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after, rules = [Path(tmp) / name for name in ('before.txt', 'after.txt', 'rules.json')]
            before.write_text('کیفیت بی‌نظیر', encoding='utf-8')
            after.write_text('این پارچه از پنبه ساخته شده است.', encoding='utf-8')
            rules.write_text(json.dumps({'rules': load_rules()[:1]}), encoding='utf-8')
            result = cli(before, after, '--lang', 'fa', '--json')
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload), 2)
            self.assertEqual(payload[0]['source'], str(before))
            self.assertEqual(payload[1]['findings'], [])
            rendered = cli(before, after, '--lang', 'fa')
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertNotIn('->', rendered.stdout)
            custom = cli(before, '--lang', 'fa', '--lexicon', rules, '--json')
            self.assertEqual(json.loads(custom.stdout)['findings'], [])

    def test_invalid_language(self):
        self.assertEqual(cli('--lang', 'auto').returncode, 2)


class EnglishContractTests(unittest.TestCase):
    def test_default_and_explicit_english_cli_against_original(self):
        samples = ['', 'Hello everyone! In this video I will show you how.',
                   "I don't want you to waste 30 minutes on a script. You can start with a useful example, explain what changed, and show the result before asking anyone to save it.",
                   'We use a robust system — it works seamlessly.']
        for text in samples:
            for options in [[], ['--json']]:
                with self.subTest(text=text, options=options):
                    old = cli('-', *options, text=text, original=True)
                    for lang in [[], ['--lang', 'en']]:
                        new = cli('-', *options, *lang, text=text)
                        self.assertEqual((new.returncode, new.stdout, new.stderr), (old.returncode, old.stdout, old.stderr))

    def test_english_compare_and_custom_lexicon(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ('a.txt', 'b.txt')]
            for p, text in zip(paths, ['Unlock a seamless experience.', "Don't waste your time. Show a useful example first."]):
                p.write_text(text, encoding='utf-8')
            for options in [[], ['--json'], ['--json', '--lexicon', HUMAN / 'slop.json']]:
                old = cli(*paths, *options, original=True)
                for lang in [[], ['--lang', 'en']]:
                    new = cli(*paths, *options, *lang)
                    self.assertEqual((new.returncode, new.stdout, new.stderr), (old.returncode, old.stdout, old.stderr))
            payload = json.loads(cli(*paths, '--json').stdout)
            self.assertEqual(set(payload[0]), {'source', 'checks', 'human_score', 'verdict'})
            self.assertEqual(set(payload[0]['checks']), {'BURSTINESS', 'SPECIFICITY', 'SLOP DENSITY', 'FINGERPRINT', 'VOICE'})


if __name__ == '__main__':
    unittest.main()
