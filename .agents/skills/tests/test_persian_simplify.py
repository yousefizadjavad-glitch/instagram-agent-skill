"""35 design cases and independent version-two/legacy contracts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HUMAN = Path(__file__).resolve().parents[1] / 'ig-human'
sys.path.insert(0, str(HUMAN))
from persian_simplify import simplify
from persian_rewrite import suggest
from persian_rewrite_checks import mark_conflicts, validate_selection
from persian_simplify_checks import validate

# outcome: replacement present (P), no patch with guidance/abstention (A), no patch (N).
CASES = [
 ('امروز این مدل را امتحان کردم؛ سبک و راحت بود.', None, [], 'N'),
 ('امروز این مدل رو امتحان کردم؛ خیلی راحت بود.', 'colloquial', [], 'N'),
 ('در خصوص ارسال سفارش سؤال دارم.', 'formal', [], 'P'),
 ('به منظور بررسی محصول، بسته را باز می‌کنم.', 'semi-formal', [], 'P'),
 ('فایل را از طریق ایمیل ارسال کنید.', 'semi-formal', [], 'P'),
 ('مسیر از طریق تونل ادامه دارد.', None, [], 'N'),
 ('خواهشمند است تصویر رسید را ارسال فرمایید.', 'formal', [], 'P'),
 ('خواهشمند است تصویر رسید را ارسال فرمایید.', 'colloquial', [], 'P'),
 ('شما تصویر رسید را ارسال فرمایید.', None, [], 'N'),
 ('تو عکس رو بفرست.', 'formal', [], 'N'),
 ('این محصول موجود می‌باشد.', None, [], 'A'),
 ('ثبت درخواست انجام می‌پذیرد.', None, [], 'A'),
 ('جهت شمال را دنبال کنید.', None, [], 'N'),
 ('در راستای دیوار حرکت کنید.', None, [], 'N'),
 ('ارسال این سفارش رایگان نمی‌باشد.', None, [], 'A'),
 ('اگر پرداخت تأیید شود، ارسال صورت می‌گیرد.', None, [], 'A'),
 ('این روش ممکن است موجب کاهش هزینه شود.', None, [], 'N'),
 ('صرفاً در صورت تأیید مدیر، وجه مسترد می‌شود.', None, [], 'N'),
 ('قیمت به میزان ۲۵۰٬۰۰۰ تومان تعیین شده است.', None, [], 'A'),
 ('در خصوص مدل X200 توضیح می‌دهم.', None, [], 'P'),
 ('در خصوص برند نو توضیح می‌دهم.', None, ['در خصوص برند نو'], 'N'),
 ('ثبت‌نام تا ۱۴۰۵/۰۸/۱۰ ادامه دارد.', None, [], 'N'),
 ('اطلاعات از طریق https://example.com/a در دسترس است.', None, [], 'N'),
 ('لطفاً به @brand پیام دهید. #ثبت_سفارش', None, [], 'N'),
 ('او گفت: «خواهشمند است رسید را ارسال فرمایید.»', None, [], 'A'),
 ('او نوشت: «به منظور بررسی', None, [], 'A'),
 ('مشتری: خواهشمند است رسید ارسال شود.', None, [], 'N'),
 ('در این قرارداد، اقدامات لازم به عمل خواهد آمد.', None, [], 'A'),
 ('چه خدمات سریعی؛ پاسخ فقط سه هفته طول کشید!', None, [], 'N'),
 ('در خصوص ارسال، در خصوص زمان تحویل سؤال دارم.', None, [], 'P'),
 ('به منظور بررسی دقیق‌تر محصول، بسته را باز می‌کنم.', None, [], 'P'),
 ('😀 در خصوص Export 1080p توضیح می‌دهم.', None, [], 'P'),
 ('برای بررسی این مدل ابتدا بسته را باز می‌کنم و سپس قطعات را روی میز قرار می‌دهم و بعد هر قطعه را جداگانه نشان می‌دهم و در پایان روش نصب قطعات را با یک مثال ساده توضیح می‌دهم.', None, [], 'A'),
 ('به استحضار می‌رساند جلسه فردا برگزار می‌شود.', 'formal', [], 'A'),
 ('برای بررسی محصول، بسته را باز می‌کنم.', None, [], 'N'),
]


class DesignCases(unittest.TestCase):
    pass


def design(case):
    def test(self):
        text, tone, protect, expected = case
        report = simplify(text, protect, tone)
        if expected == 'P': self.assertTrue(report['suggestions'])
        else: self.assertFalse(report['suggestions'])
        if expected == 'A': self.assertTrue(report['guidance'] or report['abstentions'])
        for s in report['suggestions'] + report['guidance'] + report['abstentions']:
            self.assertEqual(text[s['start']:s['end']], s['before'])
        for s in report['suggestions']:
            self.assertTrue(s['requires_confirmation'])
            self.assertTrue(s['reason'])
            self.assertNotEqual(s['before'], s['replacement'])
    return test


for i, case in enumerate(CASES, 1):
    setattr(DesignCases, f'test_design_{i:02}', design(case))


def cli(text, *args):
    return subprocess.run([sys.executable, '-B', str(HUMAN/'persian_rewrite.py'), '-', *args],
                          input=text.encode(), capture_output=True, cwd='/tmp')


class SimplificationContracts(unittest.TestCase):
    def test_exact_replacements(self):
        for text, expected in [('در خصوص ارسال سفارش', 'دربارهٔ'), ('به منظور بررسی محصول', 'برای'),
                               ('فایل را از طریق ایمیل ارسال کنید.', 'با ایمیل'),
                               ('خواهشمند است فایل را ارسال فرمایید.', 'لطفاً فایل را ارسال کنید')]:
            self.assertEqual(simplify(text)['suggestions'][0]['replacement'], expected)

    def test_tone_variants(self):
        text = 'خواهشمند است فایل را ارسال فرمایید.'
        self.assertEqual(simplify(text, target_tone='formal')['suggestions'][0]['replacement'], 'لطفاً فایل را ارسال کنید')
        self.assertEqual(simplify(text, target_tone='semi-formal')['suggestions'][0]['replacement'], 'لطفاً فایل را ارسال کنید')
        self.assertEqual(simplify(text, target_tone='colloquial')['suggestions'][0]['replacement'], 'لطفاً فایل را بفرستید')

    def test_barriers_in_same_sentence(self):
        for marker in ['نیست', 'اگر', 'ممکن است', 'صرفاً', 'در صورت', 'قرارداد', 'شما', 'تو', 'احتمالاً', 'تضمینی', 'نشود', 'ندارد', 'مقررات']:
            report = simplify('در خصوص ارسال سفارش '+marker+' توضیح می‌دهم.')
            self.assertFalse(report['suggestions'], marker)
            self.assertTrue(report['abstentions'], marker)

    def test_complete_request_and_word_boundaries(self):
        for text in ['خواهشمند است فایل را ارسال فرمایید و حذف کنید.', 'خواهشمند است فایل را', 'در خصوصیت ارسال', 'به منظوریت بررسی', 'از طریق ایمیل نامعلوم']:
            self.assertFalse(simplify(text)['suggestions'], text)

    def test_dedup_and_independent_occurrences(self):
        report = simplify(CASES[29][0])
        self.assertEqual(len(report['suggestions']), 2)
        self.assertEqual(len({(s['start'], s['end'], s['replacement']) for s in report['suggestions']}), 2)

    def test_cross_mechanical_conflicts(self):
        text = 'به منظور  بررسی محصول'
        result = cli(text, '--simplify', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        all_items = report['suggestions'] + report['simplification']['suggestions']
        real = json.loads(cli('خواهشمند است تصویر  رسید را ارسال فرمایید.', '--simplify', '--json').stdout)
        m = real['suggestions'][0]; l = real['simplification']['suggestions'][0]
        self.assertIn(l['id'], m['conflicts_with'])
        self.assertIn(m['id'], l['conflicts_with'])
        with self.assertRaises(ValueError): validate_selection([m, l], [m['id'], l['id']])
        # Use a synthetic wider language patch to exercise cross-category conflict protection.
        all_items.append(dict(id='l-wide', start=0, end=len(text)))
        mark_conflicts(all_items)
        with self.assertRaises(ValueError): validate_selection(all_items, [all_items[0]['id'], 'l-wide'])

    def test_cli_versions_and_no_apply(self):
        text = 'سلام  دوستان؛ در خصوص ارسال سفارش'
        old = cli(text, '--json'); new = cli(text, '--simplify', '--json')
        self.assertEqual(old.returncode, 0); self.assertEqual(new.returncode, 0)
        a, b = json.loads(old.stdout), json.loads(new.stdout)
        self.assertEqual(a, suggest(text))
        self.assertEqual(a['schema_version'], 1); self.assertNotIn('simplification', a)
        self.assertEqual(b['schema_version'], 2)
        self.assertTrue(b['simplification']['suggestions'])
        for args in [('--apply',), ('--target-tone','formal'), ('--simplify','--target-tone','auto')]:
            self.assertEqual(cli('', *args).returncode, 2)
        for tone in ['formal','semi-formal','colloquial']:
            r=cli('در خصوص ارسال سفارش', '--simplify','--target-tone',tone,'--json')
            self.assertEqual(json.loads(r.stdout)['simplification']['target_tone'],tone)

    def test_file_english_crlf_and_nonmutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.txt'; raw='😀 در خصوص Export 1080p\r\nسلام  دوستان'.encode();p.write_bytes(raw)
            r=subprocess.run([sys.executable,'-B',str(HUMAN/'persian_rewrite.py'),str(p),'--simplify','--json'],capture_output=True,cwd='/tmp')
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(p.read_bytes(),raw)
            report=json.loads(r.stdout);self.assertEqual(report['source_text'],raw.decode())
            for s in report['simplification']['suggestions']:
                self.assertEqual(raw.decode()[s['start']:s['end']],s['before'])
            self.assertEqual(list(Path(tmp).iterdir()),[p])
        r=cli('Please send the file.', '--simplify','--json')
        self.assertFalse(json.loads(r.stdout)['simplification']['suggestions'])

    def test_protection_idempotence_and_validation(self):
        text='در خصوص مدل X200 توضیح می‌دهم.'
        r=simplify(text);s=r['suggestions'][0]
        preview=text[:s['start']]+s['replacement']+text[s['end']:]
        self.assertIn('X200',preview);self.assertFalse(simplify(preview)['suggestions'])
        for text in ['«در خصوص ارسال»', '«در خصوص ارسال', 'مشتری: در خصوص ارسال', 'در خصوص ارسال سفارش با کنایه']:
            self.assertFalse(simplify(text)['suggestions'])
        with self.assertRaises(ValueError):simplify('',target_tone='auto')


if __name__=='__main__': unittest.main()
