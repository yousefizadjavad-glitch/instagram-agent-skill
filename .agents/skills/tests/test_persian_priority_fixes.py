"""Focused regressions from the artificial 30-text quality exercise."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

HUMAN = Path(__file__).resolve().parents[1] / 'ig-human'
sys.path[:0] = [str(HUMAN), str(HUMAN.parent)]
from persian_simplify import simplify
from persian_simplify_checks import NEGATION
from persian_tone import review_tone
from persian_rewrite import suggest
from persian_protection import protected_spans

NEGATIVES = ['ندارم', 'نداری', 'نداریم', 'ندارید', 'ندارند', 'نیستم', 'نیستیم',
             'نبودم', 'نبودند', 'نشدم', 'نشوند', 'نخواهم', 'نخواهید', 'نکنید',
             'نداشته‌ام', 'نداشته ایم', 'نتوانستم', 'نتوانند', 'نمی‌دانم',
             'نمی دانیم', 'نمیدانم', 'هرگز', 'هیچ']
COUNTERS = ['دارم', 'دارند', 'هستم', 'بودیم', 'شدند', 'خواهم', 'توانستم',
            'نامدار', 'نادری', 'نداریان', 'نیستان', 'نکات', 'نخواهشی']


class NegativeFamilies(unittest.TestCase):
    pass


def negative_case(word):
    def test(self):
        text = 'در خصوص ارسال سفارش توضیح ' + word + '.'
        self.assertIsNotNone(NEGATION.search(text))
        result = simplify(text)
        self.assertFalse(result['suggestions'])
        self.assertTrue(result['abstentions'])
    return test


def counter_case(word):
    def test(self):
        text = 'در خصوص ارسال سفارش توضیح ' + word + '.'
        self.assertIsNone(NEGATION.search(text))
        self.assertTrue(simplify(text)['suggestions'])
    return test


for i, word in enumerate(NEGATIVES):
    setattr(NegativeFamilies, f'test_negative_{i:02}', negative_case(word))
for i, word in enumerate(COUNTERS):
    setattr(NegativeFamilies, f'test_counter_{i:02}', counter_case(word))


class PriorityRegressions(unittest.TestCase):
    def shifts(self, text):
        return [f for f in review_tone(text)['findings'] if f['rule_id'] == 'fa-address-shift']

    def test_R10(self):
        result = simplify('در خصوص ارسال سفارش اطلاع ندارم.')
        self.assertFalse(result['suggestions'])
        self.assertEqual(result['abstentions'][0]['reason'], 'negation_requires_review')

    def test_S3_and_single_newline(self):
        for separator in ['.\n', '.\n\n', '.\r\n\r\n', '؛ ']:
            self.assertEqual(len(self.shifts('شما بخوانید' + separator + 'تو می‌تونی نظر بدی.')), 1)

    def test_S4_and_reverse(self):
        for text in ['شما سفارش را ثبت کنید؛ تو هزینه را پرداخت کن.',
                     'تو هزینه را پرداخت کن؛ شما سفارش را ثبت کنید.']:
            findings = self.shifts(text)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]['attribution'], 'requires_context_review')
            self.assertEqual(len(findings[0]['evidence']), 2)
            for e in findings[0]['evidence']:
                self.assertEqual(text[e['start']:e['end']], e['evidence'])

    def test_quote_and_dialogue_barriers(self):
        for text in ['شما سفارش را ثبت کنید؛ «تو هزینه را پرداخت کن».',
                     '«شما بخوانید.\n\nتو می‌تونی»',
                     '«شما بخوانید.\n\nتو می‌تونی',
                     'مشتری: شما سفارش را ثبت کنید.\nپشتیبان: تو هزینه را پرداخت کن.',
                     'شما بخوانید. «نقل‌قول» تو می‌تونی ادامه بدی.',
                     'او گفت شما سفارش را ثبت کنید؛ تو هزینه را پرداخت کن.']:
            self.assertFalse(self.shifts(text), text)

    def test_audience_switches(self):
        for marker in ['دانش‌آموز عزیز،', 'خطاب به کودک:', 'مخاطب بعدی:', 'تغییر مخاطب:']:
            text = 'والدین عزیز، شما سفارش را ثبت کنید.\n\n' + marker + ' تو هزینه را پرداخت کن.'
            self.assertFalse(self.shifts(text), text)

    def test_register_scope_is_unchanged(self):
        result = review_tone('مقتضی است فرم تکمیل شود.\n\nبزن بریم؛ یادت نره.')
        self.assertFalse(any(f['rule_id'] == 'fa-mixed-register' for f in result['findings']))

    def test_ambiguous_or_distant_address(self):
        for text in ['تو خونه بمون؛ شما سفارش را ثبت کنید.',
                     'دوست تو آمد. شما سفارش را ثبت کنید.',
                     'شما بخوانید.\n\n\nتو می‌تونی نظر بدی.',
                     'شما بخوانید. یک بخش تمام شد. موضوع دیگری شروع شد. تو می‌تونی نظر بدی.',
                     'شما بخوانید.\n---\nتو می‌تونی نظر بدی.']:
            self.assertFalse(self.shifts(text), text)

    def test_C10_explicit_and_cue_only(self):
        text = 'برند  نو امروز در نمایشگاه حاضر است. سلام  دوستان'
        for protect in [[], ['برند  نو']]:
            result = suggest(text, protect)
            self.assertEqual(len(result['suggestions']), 1)
            self.assertEqual(result['suggestions'][0]['start'], text.rindex('  '))
            self.assertTrue(result['abstentions'])
            self.assertTrue(any('--protect' in l for l in result['limitations']))
        result = suggest(text)
        self.assertTrue(any(s['reason'] == 'suspected_name_context' for s in result['protected_spans']))
        self.assertTrue(any('تشخیص داده نشده' in l for l in result['limitations']))

    def test_no_generic_name_guess(self):
        text = 'سپیدار  نو در نمایشگاه حاضر است.'
        result = suggest(text)
        self.assertFalse(any(s['reason'] == 'suspected_name_context' for s in result['protected_spans']))
        self.assertTrue(result['suggestions'])
        self.assertFalse(suggest(text, ['سپیدار  نو'])['suggestions'])
        self.assertTrue(any('--protect' in l for l in result['limitations']))

    def test_cues_protect_language_and_literal_variants(self):
        for prefix in ['برند', 'نام تجاری', 'نام محصول']:
            text = prefix + ' در خصوص ارسال؛ سلام  دوستان'
            self.assertFalse(simplify(text)['suggestions'])
            self.assertEqual(len(suggest(text)['suggestions']), 1)
        self.assertFalse(suggest('برندسازی  امروز')['protected_spans'])
        text='نام  (نو)+ و نام  (نو)+'
        self.assertFalse(suggest(text, ['نام  (نو)+'])['suggestions'])

    def test_negation_boundaries_and_quotes(self):
        result = simplify('در خصوص ارسال سفارش اطلاع ندارم. به منظور بررسی محصول آماده‌ام.')
        self.assertEqual(len(result['suggestions']), 1)
        self.assertEqual(result['suggestions'][0]['replacement'], 'برای')
        self.assertFalse(simplify('«در خصوص ارسال اطلاع ندارم»')['suggestions'])
        self.assertTrue(simplify('در خصوص ارسال سفارش اطلاع دارم.')['suggestions'])

    def test_cli_schema_and_source(self):
        script=HUMAN/'persian_rewrite.py'
        text='برند  نو امروز حاضر است. سلام  دوستان'
        r=subprocess.run([sys.executable,'-B',str(script),'-','--json'],input=text,text=True,capture_output=True,cwd='/tmp')
        self.assertEqual(r.returncode,0,r.stderr)
        out=json.loads(r.stdout)
        self.assertEqual(out['schema_version'],1)
        self.assertEqual(out['source_text'],text)
        r=subprocess.run([sys.executable,'-B',str(script),'-','--simplify','--json'],input='در خصوص ارسال اطلاع ندارم.',text=True,capture_output=True,cwd='/tmp')
        self.assertEqual(r.returncode,0,r.stderr)
        out=json.loads(r.stdout)
        self.assertEqual(out['schema_version'],2)
        self.assertFalse(out['simplification']['suggestions'])


if __name__ == '__main__': unittest.main()
