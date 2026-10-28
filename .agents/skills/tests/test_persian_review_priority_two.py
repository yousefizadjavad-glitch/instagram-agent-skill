"""Narrow contextual exceptions; synthetic fixtures, not quality calibration."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HUMAN = Path(__file__).resolve().parents[1] / 'ig-human'
sys.path[:0] = [str(HUMAN), str(HUMAN.parent)]
from persian_review import review

# Each fixture specifies only the affected warning family; other findings remain independent.
CASES = [
 ('absolute_promise', 'این موفقیت تضمینی نیست؛ نتیجه به تمرین بستگی دارد.', False),
 ('absolute_promise', 'این موفقیت تضمینی نیست.', False),
 ('absolute_promise', 'نتیجه تضمینی نیست.', False),
 ('absolute_promise', 'موفقیت صددرصد تضمینی نبود.', False),
 ('absolute_promise', 'موفقیت ۱۰۰٪ تضمینی نیست.', False),
 ('absolute_promise', 'موفقیت تضمینی نبوده است.', False),
 ('absolute_promise', 'موفقیت تضمینی است.', True),
 ('absolute_promise', 'شاید این موفقیت تضمینی نیست.', True),
 ('absolute_promise', 'اگر موفقیت تضمینی نیست، تمرین کنید.', True),
 ('absolute_promise', 'موفقیت تضمینی نیست؟', True),
 ('absolute_promise', 'این موفقیت تضمینی نیست مگر با تلاش.', True),
 ('absolute_promise', 'اینکه موفقیت تضمینی نیست درست نیست.', True),
 ('absolute_promise', 'نمی‌توان گفت موفقیت تضمینی نیست.', True),
 ('absolute_promise', 'موفقیت تضمینی\nنیست.', True),
 ('absolute_promise', 'موفقیت تضمینی نیستندار.', True),
 ('absolute_promise', 'اینکه موفقیت تضمینی نیست.', True),
 ('absolute_promise', 'ظاهراً این موفقیت تضمینی نیست.', True),
 ('absolute_promise', '«موفقیت تضمینی» نیست.', True),
 ('absolute_promise', '«موفقیت تضمینی نیست».', False),
 ('absolute_promise', '«موفقیت تضمینی است».', True),
 ('absolute_promise', 'برای Reel این موفقیت تضمینی نیست.', False),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟ نظرتان را بنویسید.', False),
 ('generic_engagement', 'کدام رنگ برای میز کوچک مناسب‌تر است؟ نظرتان را بنویسید.', False),
 ('generic_engagement', 'کدوم مدل رو ترجیح می‌دی؟ نظرتون رو بگین.', False),
 ('generic_engagement', 'کدام طرح بهتر است? نظرتان را بنویسید.', False),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟\nنظرتان را بنویسید.', False),
 ('generic_engagement', 'نظرتان را بنویسید.', True),
 ('generic_engagement', 'هوا چطور است؟ نظرتان را بنویسید.', True),
 ('generic_engagement', '؟ نظرتان را بنویسید.', True),
 ('generic_engagement', 'آیا محصول موجود است؟ نظرتان را بنویسید.', True),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟ ارسال فرداست. نظرتان را بنویسید.', True),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟\n\nنظرتان را بنویسید.', True),
 ('generic_engagement', '«کدام رنگ را ترجیح می‌دهید؟» نظرتان را بنویسید.', True),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟ نظرتان را بنویسید دربارهٔ سیاست.', True),
 ('generic_engagement', 'کدام رنگ را ترجیح می‌دهید؟ لایک کنید و به اشتراک بگذارید.', True),
 ('generic_engagement', 'Which color? نظرتان را بنویسید.', True),
 ('obvious_repetition', 'خیلی خیلی خوشحالم؛ اولین گلدونم گل داد!', False),
 ('obvious_repetition', 'من خیلی خیلی خوشحالم!', False),
 ('obvious_repetition', 'خیلی خیلی ممنونم.', False),
 ('obvious_repetition', 'خیلی خیلی دلتنگم!', False),
 ('obvious_repetition', 'برای Reel خیلی خیلی خوشحالم!', False),
 ('obvious_repetition', '«خیلی خیلی خوشحالم!»', False),
 ('obvious_repetition', 'خیلی خیلی خیلی خوشحالم!', True),
 ('obvious_repetition', 'خیلی خیلی خوبه.', True),
 ('obvious_repetition', 'خانه‌ها خانه‌ها زیبا هستند.', True),
 ('obvious_repetition', 'خیلی خیلی خوشحالم؟', True),
 ('obvious_repetition', 'شاید خیلی خیلی خوشحالم.', True),
 ('obvious_repetition', 'خیلی خیلی خوشحالم نیستم.', True),
 ('obvious_repetition', 'خیلی خیلی خوشحالم که سه هفته معطل شدم.', True),
]


class ContextFixtures(unittest.TestCase):
    pass


def fixture(kind, text, expected):
    def test(self):
        result = review(text)
        found = [f for f in result['findings'] if f['warning_type'] == kind]
        self.assertEqual(bool(found), expected, text)
        self.assertEqual(result['text'], text)
        for f in result['findings']:
            self.assertEqual(text[f['start']:f['end']], f['evidence'])
            self.assertIn(f['attribution'], ['requires_context_review', 'requires_quote_review'])
    return test


for i, case in enumerate(CASES, 1):
    setattr(ContextFixtures, f'test_context_{i:02}', fixture(*case))


class ReviewContracts(unittest.TestCase):
    def cli(self, text, *args):
        return subprocess.run([sys.executable,'-B',str(HUMAN/'detect.py'),'-','--lang','fa',*args],
                              input=text, text=True, capture_output=True, cwd='/tmp')

    def test_three_targets_cli_and_json(self):
        for text in ['این موفقیت تضمینی نیست؛ نتیجه به تمرین بستگی دارد.',
                     'کدام رنگ را ترجیح می‌دهید؟ نظرتان را بنویسید.',
                     'خیلی خیلی خوشحالم؛ اولین گلدونم گل داد!']:
            r=self.cli(text,'--json')
            self.assertEqual(r.returncode,0,r.stderr)
            report=json.loads(r.stdout)
            self.assertEqual(report['findings'],[])
            self.assertEqual(set(report),{'source','language','mode','text','word_count','notice','findings'})
            self.assertEqual(report['text'],text)
            rendered=self.cli(text)
            self.assertEqual(rendered.returncode,0)
            self.assertIn('در محدودهٔ قواعد اولیه',rendered.stdout)

    def test_independent_claims_and_emphasis(self):
        text='این موفقیت تضمینی نیست. موفقیت تضمینی است. خیلی خیلی خوشحالم! خانه‌ها خانه‌ها.'
        findings=review(text)['findings']
        self.assertEqual([f['warning_type'] for f in findings],['absolute_promise','obvious_repetition'])
        self.assertEqual(findings[0]['start'],text.index('موفقیت تضمینی',text.index('.')+1))

    def test_quote_attribution_remains(self):
        text='او نوشت: «موفقیت تضمینی است و خانه‌ها خانه‌ها». این ادعا درست نیست.'
        findings=review(text)['findings']
        self.assertEqual(len(findings),2)
        self.assertTrue(all(f['quoted'] and f['attribution']=='requires_quote_review' for f in findings))
        # A quote boundary must not provide negation or a question to another voice.
        self.assertTrue(review('«موفقیت تضمینی» نیست.')['findings'])

    def test_mixed_unicode_offsets(self):
        text='😀 برای Reel این موفقیت تضمینی نیست. كيفيت بي‌نظير؛ خانه‌ها خانه‌ها.'
        findings=review(text)['findings']
        self.assertEqual([f['warning_type'] for f in findings],['vague_promotion','obvious_repetition'])
        for f in findings:self.assertEqual(text[f['start']:f['end']],f['evidence'])

    def test_no_rewrite_file_and_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a.txt',Path(tmp)/'b.txt'
            raw='این موفقیت تضمینی نیست.\r\nخیلی خیلی خوشحالم!'.encode()
            a.write_bytes(raw);b.write_text('موفقیت تضمینی است.',encoding='utf-8')
            result=subprocess.run([sys.executable,'-B',str(HUMAN/'detect.py'),str(a),str(b),'--lang','fa','--json'],capture_output=True,text=True,cwd='/tmp')
            self.assertEqual(result.returncode,0,result.stderr)
            reports=json.loads(result.stdout)
            self.assertFalse(reports[0]['findings']);self.assertTrue(reports[1]['findings'])
            self.assertEqual(a.read_bytes(),raw)
            self.assertEqual(set(Path(tmp).iterdir()),{a,b})

    def test_custom_rules_not_reclassified(self):
        rule={'id':'custom-repetition','warning_type':'obvious_repetition','pattern':r'(?P<word>خیلی) خیلی',
              'reason':'custom','suggestion':'custom','exceptions':['custom'],'tones':['custom']}
        self.assertTrue(review('خیلی خیلی خوشحالم!', [rule])['findings'])


if __name__=='__main__':unittest.main()
