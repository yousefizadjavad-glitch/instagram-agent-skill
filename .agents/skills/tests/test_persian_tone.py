"""Tone design examples, abstention, offsets and opt-in CLI contracts."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HUMAN = ROOT / '.agents/skills/ig-human'
sys.path[:0] = [str(HUMAN), str(HUMAN.parent)]
from persian_tone import review_tone, render_tone
from persian_review import review

# Expected rule IDs concern tone_review only, never the legacy lexical review.
CASES = [
 ('شما می‌توانید رنگ را انتخاب کنید. تو می‌تونی اندازه را هم عوض کنی.', None, 'unspecified', {'fa-address-shift'}),
 ('تو می‌تونی رنگ رو انتخاب کنی. شما می‌توانید سفارش را ثبت کنید.', None, 'unspecified', {'fa-address-shift'}),
 ('شما می‌توانید رنگ را انتخاب کنید و سفارش را ثبت کنید.', None, 'unspecified', set()),
 ('تو می‌تونی رنگ رو انتخاب کنی و سفارشت رو ثبت کنی.', 'colloquial', 'to', set()),
 ('شما می‌تونین رنگ رو انتخاب کنین.', 'colloquial', 'shoma', set()),
 ('این مدل تو خونه جا می‌شه.', None, 'unspecified', set()),
 ('تو این ویدئو، شما مراحل را می‌بینید.', None, 'unspecified', set()),
 ('تو می‌تونی همین حالا سفارشت رو ثبت کنی.', 'formal', 'shoma', {'fa-target-address', 'fa-target-tone'}),
 ('مقتضی است فرم رو پر کنی؛ یادت نره.', None, 'unspecified', {'fa-mixed-register'}),
 ('به استحضار می‌رساند ثبت‌نام آغاز شده است.', 'formal', 'unspecified', set()),
 ('مقتضی است درخواست خود را ثبت فرمایید.', 'colloquial', 'unspecified', {'fa-target-tone'}),
 ('سلام، لطفاً شمارهٔ سفارش را ارسال کنید.', 'semi-formal', 'unspecified', set()),
 ('او گفت: «تو می‌تونی». شما فرم را تکمیل کنید.', None, 'unspecified', set()),
 ('مشتری: تو می‌تونی کمک کنی؟\nپشتیبان: شما شمارهٔ سفارش را بفرستید.', None, 'unspecified', set()),
 ('شما بخوانید: «او گفت “تو می‌تونی” و رفت».', None, 'unspecified', set()),
 ('شما بخوانید. او گفت: «تو می‌تونی ادامه بدی', None, 'unspecified', set()),
 ('سلام، بفرمایید.', None, 'unspecified', set()),
 ('شما انتخاب کنید؛ تو می‌تونی.', None, 'unspecified', {'fa-address-shift'}),
 ('والدین عزیز، شما فرم را بخوانید. دانش‌آموز عزیز، تو پاسخ بده.', None, 'unspecified', set()),
 ('واژه‌های «تو» و «شما» دو نوع خطاب‌اند.', None, 'unspecified', set()),
 ('شما می‌توانید Reel بسازید؛ تو می‌تونی منتشرش کنی 😀', None, 'unspecified', {'fa-address-shift'}),
 ('گفت تو باید بروی؛ شما فعلاً منتظر بمانید.', None, 'unspecified', set()),
 ('- شما رنگ را انتخاب کنید.\n- شما اندازه را مشخص کنید.', None, 'unspecified', set()),
]


def cli(text, *args):
    return subprocess.run([sys.executable, '-B', str(HUMAN / 'detect.py'), '-', *args],
                          input=text, text=True, capture_output=True, cwd='/tmp')


class DesignExamples(unittest.TestCase):
    pass


def example(case):
    def test(self):
        text, tone, address, expected = case
        result = review_tone(text, tone, address)
        self.assertEqual({f['rule_id'] for f in result['findings']}, expected)
        for finding in result['findings']:
            self.assertTrue(finding['reason'])
            self.assertTrue(finding['suggestion'])
            self.assertEqual(finding['attribution'], 'requires_context_review')
            for evidence in finding['evidence']:
                self.assertEqual(text[evidence['start']:evidence['end']], evidence['evidence'])
    return test


for index, case in enumerate(CASES, 1):
    setattr(DesignExamples, f'test_design_{index:02}', example(case))


class ToneContracts(unittest.TestCase):
    def test_short_and_empty_abstention(self):
        for text in ['', 'سلام', 'شما', 'تو خونه', 'سلام، بفرمایید.']:
            self.assertEqual(review_tone(text)['assessment'], 'insufficient_evidence')
        self.assertEqual(review_tone(CASES[17][0])['assessment'], 'findings_present')

    def test_sufficient_consistent_and_independent_targets(self):
        self.assertEqual(review_tone('شما بخوانید. شما انتخاب کنید.')['assessment'], 'no_findings')
        self.assertFalse(review_tone('شما می‌تونین انتخاب کنین.', 'colloquial', 'shoma')['findings'])
        self.assertEqual({f['rule_id'] for f in review_tone('تو می‌تونی.', target_address='shoma')['findings']}, {'fa-target-address'})

    def test_quote_variants_and_barriers(self):
        for left, right in [('«', '»'), ('“', '”'), ('‘', '’'), ('"', '"'), ("'", "'")]:
            text = f'شما بخوانید؛ {left}مقتضی است تو می‌تونی؛ یادت نره{right} تو می‌تونی.'
            result = review_tone(text)
            self.assertFalse(result['findings'])
            self.assertTrue(result['excluded_spans'])
        self.assertFalse(review_tone('شما بخوانید. «تو می‌تونی')['findings'])
        # Adjacent paragraphs may continue the same audience (S3 regression).
        self.assertEqual(review_tone('شما بخوانید.\n\nتو می‌تونی')['findings'][0]['rule_id'], 'fa-address-shift')

    def test_offsets_unicode_and_normalized_matching(self):
        text = '😀 مُحتوا\nشما مي‌توانيد بخوانید؛ تو مي‌توني ادامه بدی.'
        result = review_tone(text)
        finding = result['findings'][0]
        self.assertEqual(finding['rule_id'], 'fa-address-shift')
        self.assertEqual(len(finding['evidence']), 2)
        for e in finding['evidence']:
            self.assertEqual(text[e['start']:e['end']], e['evidence'])

    def test_general_words_and_weak_morphology(self):
        for text in ['سلام شما لطفاً ثبت کنید.', 'دوست تو رسید. شما آمدید.', 'انتخاب کنید و برو.']:
            self.assertFalse(review_tone(text)['findings'])

    def test_cli_opt_in_and_json_preservation(self):
        text = CASES[0][0]
        old = cli(text, '--lang', 'fa', '--json')
        enabled = cli(text, '--lang', 'fa', '--tone-check', '--json')
        self.assertEqual((old.returncode, enabled.returncode), (0, 0))
        a, b = json.loads(old.stdout), json.loads(enabled.stdout)
        self.assertNotIn('tone_review', a)
        self.assertTrue(b.pop('tone_review')['findings'])
        self.assertEqual(a, b)
        self.assertEqual({k: v for k, v in a.items() if k != 'source'}, review(text))

    def test_cli_implicit_activation_and_rejection(self):
        for options in [('--target-tone', 'formal'), ('--target-address', 'shoma'),
                        ('--target-address', 'unspecified'), ('--tone-check',)]:
            good = cli('تو می‌تونی.', '--lang', 'fa', '--json', *options)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn('tone_review', json.loads(good.stdout))
            for lang in [(), ('--lang', 'en')]:
                bad = cli('', *lang, *options)
                self.assertEqual(bad.returncode, 2)
                self.assertIn('require --lang fa', bad.stderr)
        for flag, value in [('--target-tone', 'auto'), ('--target-address', 'you')]:
            self.assertEqual(cli('', '--lang', 'fa', flag, value).returncode, 2)

    def test_cli_text_and_compare(self):
        result = cli(CASES[0][0], '--lang', 'fa', '--tone-check')
        self.assertEqual(result.returncode, 0)
        self.assertIn('بررسی سازگاری لحن', result.stdout)
        self.assertIn('پیشنهاد:', result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.txt', Path(tmp)/'b.txt'
            a.write_text(CASES[0][0]); b.write_text('سلام')
            result = subprocess.run([sys.executable, '-B', str(HUMAN/'detect.py'), str(a), str(b),
                                     '--lang', 'fa', '--tone-check', '--json'], capture_output=True, text=True, cwd='/tmp')
            self.assertEqual(result.returncode, 0, result.stderr)
            reports = json.loads(result.stdout)
            self.assertEqual(len(reports), 2)
            self.assertEqual(reports[0]['tone_review']['assessment'], 'findings_present')
            self.assertEqual(reports[1]['tone_review']['assessment'], 'insufficient_evidence')

    def test_no_scoring_or_rewrite(self):
        text = CASES[8][0]
        self.assertEqual(review(text)['text'], text)
        result = review_tone(text)
        self.assertFalse({'score', 'human_score', 'verdict', 'rewritten_text'} & result.keys())
        out = io.StringIO(); render_tone(result, out)
        self.assertIn('محدودیت', out.getvalue())

    def test_validation(self):
        with self.assertRaises(ValueError): review_tone('', 'auto')
        with self.assertRaises(ValueError): review_tone('', target_address='you')


if __name__ == '__main__':
    unittest.main()
