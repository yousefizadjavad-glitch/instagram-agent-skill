"""Synthetic safety regressions; no claims of semantic or name completeness."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HUMAN=Path(__file__).resolve().parents[1]/'ig-human'
sys.path[:0]=[str(HUMAN),str(HUMAN.parent)]
from persian_simplify import simplify
from persian_simplify_checks import PROHIBITION
from persian_rewrite import suggest
from persian_protection import protected_spans
from persian_tone import review_tone
from persian_dialogue import labelled_dialogue_spans

SAMPLES={
 'V02':'به منظور آزمایش مدار، نباید خازن باردار را لمس کرد؛ پیش از نمایش، انرژی ذخیره‌شده را تخلیه می‌کنم.',
 'K10':'مجموعهٔ سفال نقش  باران در ویترین شرقی چیده شده است؛ فاصلهٔ میانی بخشی از هویت بصری این نام است.',
 'U05':'برند: ماه  نقره‌ای\nنام را همین‌طور روی مهر حک کرده‌ایم؛ فاصلهٔ میان دو واژه عمدی است.',
 'V04':'نرگس: شما بخوانید.\nآرمان: تو می‌تونی ادامه بدی؛ این بخش دیالوگ نمایش ماست.',
 'K17':'شما فایل صوتی را تا آخر گوش دهید؛ بعد تو برداشتت را زیر پست بنویس.',
 'U04':'شما شمارهٔ پرونده را یادداشت کنید.\n\nتو رسیدت را نگه دار؛ هر دو کارت برای همان متقاضی نوشته شده‌اند.',
}


class ProhibitionTests(unittest.TestCase):
    def test_V02(self):
        report=simplify(SAMPLES['V02'])
        self.assertFalse(report['suggestions'])
        self.assertEqual(report['abstentions'][0]['reason'],'prohibition_requires_review')

    def test_four_limited_forms(self):
        for phrase in ['نباید','نکنید','ممنوع است','مجاز نیست','ممنوع\tاست']:
            with self.subTest(phrase=phrase):
                text='به منظور بررسی محصول، ورود '+phrase+'.'
                self.assertIsNotNone(PROHIBITION.search(text))
                self.assertFalse(simplify(text)['suggestions'])
                self.assertTrue(simplify(text)['abstentions'])

    def test_counterexamples(self):
        for phrase in ['مجاز است','ممنوعیت ورود برداشته شد','ناممنوع است','نبایدها','ممنوع استان']:
            with self.subTest(phrase=phrase):
                self.assertIsNone(PROHIBITION.search(phrase))
                self.assertTrue(simplify('به منظور بررسی محصول، '+phrase+'.')['suggestions'])

    def test_legacy_negative_prefix_guard_remains(self):
        # The new exact prohibition matcher does not match this synthetic suffix,
        # but the pre-existing broad نکن guard must not be weakened here.
        self.assertIsNone(PROHIBITION.search('نکنیدن'))
        self.assertFalse(simplify('به منظور بررسی محصول نکنیدن.')['suggestions'])

    def test_clause_boundaries_and_quotes(self):
        text='ورود ممنوع است. به منظور بررسی محصول آماده‌ام.'
        self.assertEqual(len(simplify(text)['suggestions']),1)
        self.assertFalse(simplify('«به منظور بررسی محصول ورود ممنوع است»')['suggestions'])
        self.assertFalse(simplify('«به منظور بررسی محصول ورود ممنوع است')['suggestions'])

    def test_mechanical_policy_not_expanded(self):
        for text in ['نباید سلام  دوستان را حذف کرد.','ورود ممنوع است؛ سلام  دوستان']:
            result=suggest(text)
            self.assertEqual(len(result['suggestions']),1)
            self.assertEqual(result['suggestions'][0]['replacement'],' ')
        self.assertFalse(suggest('مجاز نیست سلام  دوستان را حذف کرد.')['suggestions']) # legacy نیست guard


class NameSafetyTests(unittest.TestCase):
    def test_K10_U05(self):
        for key in ['K10','U05']:
            report=suggest(SAMPLES[key])
            self.assertFalse(report['suggestions'],key)
            self.assertTrue(report['abstentions'],key)
            self.assertTrue(any(s['reason']=='suspected_name_context' for s in report['protected_spans']))
            self.assertTrue(any('--protect' in s for s in report['limitations']))

    def test_introduction_forms(self):
        for prefix in ['نام محصول ', 'نام مجموعه ', 'نام تجاری: ', 'برند: ', 'برند ： ',
                       'عنوان: ', 'عنوان کتاب ', 'عنوان اثر ', 'عنوان فیلم ', 'عنوان نمایشگاه ']:
            text=prefix+'ماه  روشن؛ سلام  دوستان'
            report=suggest(text)
            self.assertEqual(len(report['suggestions']),1,prefix)
            self.assertEqual(report['suggestions'][0]['start'],text.rindex('  '))
            self.assertTrue(report['abstentions'],prefix)

    def test_title_in_quotes(self):
        text='عنوان «راه  بلند» روی پوستر درج شده است.'
        self.assertFalse(suggest(text)['suggestions'])

    def test_non_name_counterexamples(self):
        for text in ['به عنوان  نمونه این متن را می‌خوانم.', 'عنوان  کنید و ادامه دهید.',
                     'برندسازی  دیجیتال تمرین می‌کنم.', 'نام مجموعه‌ها  ثبت شد.',
                     'در زمینهٔ هویت بصری مطالعه می‌کنم؛ واژه  بعدی را می‌خوانم.']:
            report=suggest(text)
            self.assertTrue(report['suggestions'],text)
            self.assertFalse(any(s['reason']=='suspected_name_context' for s in report['protected_spans']),text)

    def test_unintroduced_name_not_guessed(self):
        text='مجموعهٔ سفال نقش  باران در ویترین شرقی چیده شده است.'
        self.assertTrue(suggest(text)['suggestions'])
        self.assertFalse(suggest(text,['نقش  باران'])['suggestions'])
        self.assertFalse(any(s['reason']=='suspected_name_context' for s in protected_spans(text)))

    def test_intent_requires_all_cues(self):
        for text in ['این نام را می‌خوانم؛ واژه  بعدی', 'فاصلهٔ میانی عمدی است؛ واژه  بعدی',
                     'فاصلهٔ میانی این نام تغییر کرد؛ واژه  بعدی']:
            self.assertFalse(any(s['reason']=='suspected_name_context' for s in protected_spans(text)))
        self.assertTrue(any(s['reason']=='suspected_name_context' for s in protected_spans('نگارش این عنوان عیناً حفظ شود؛ واژه  بعدی')))

    def test_explicit_protect_and_offsets(self):
        text='😀 نام مجموعه: ماه  نقره‌ای؛ ماه  نقره‌ای در فهرست است.'
        report=suggest(text,['ماه  نقره‌ای'])
        self.assertFalse(report['suggestions'])
        self.assertEqual(sum(p['reason']=='user_protected' for p in report['protected_spans']),2)
        for p in report['protected_spans']:
            self.assertEqual(text[p['start']:p['end']],p['text'])

    def test_language_cannot_enter_named_span(self):
        for text in ['عنوان: در خصوص ارسال', 'نام مجموعه به منظور بررسی', 'برند: از طریق ایمیل ارسال کنید']:
            self.assertFalse(simplify(text)['suggestions'])


class DialogueSafetyTests(unittest.TestCase):
    def shifts(self,text):
        return [f for f in review_tone(text)['findings'] if f['rule_id']=='fa-address-shift']

    def test_V04(self):
        self.assertFalse(self.shifts(SAMPLES['V04']))
        result=review_tone(SAMPLES['V04'])
        self.assertEqual(len([p for p in result['excluded_spans'] if p['reason']=='explicit_dialogue']),2)
        self.assertFalse(suggest(SAMPLES['V04'])['suggestions'])

    def test_other_labels_with_cue(self):
        for cue in ['دیالوگ','گفت‌وگو','گفتگو','نمایشنامه']:
            text='مهتاب: شما بخوانید.\r\nکیوان: تو می‌تونی ادامه بدی؛ این '+cue+' است.'
            self.assertEqual(len(labelled_dialogue_spans(text)),2)
            self.assertFalse(self.shifts(text))

    def test_labels_without_evidence_are_not_inferred(self):
        for text in ['مهتاب: شما بخوانید.\nکیوان: تو می‌تونی ادامه بدی.',
                     'مهتاب: شما بخوانید.\nمهتاب: تو می‌تونی ادامه بدی؛ این دیالوگ است.',
                     'نکته: شما بخوانید.\nهشدار: تو می‌تونی ادامه بدی؛ دربارهٔ دیالوگ.',
                     'مهتاب: شما بخوانید.\nکیوان: تو می‌تونی ادامه بدی؛ این دیالوگ نیست.']:
            self.assertFalse(labelled_dialogue_spans(text),text)
            self.assertTrue(self.shifts(text),text)

    def test_labelled_speech_protects_mechanical(self):
        text='مهتاب: سلام  دوستان.\nکیوان: می توانم ادامه بدهم؛ این دیالوگ است.'
        report=suggest(text)
        self.assertFalse(report['suggestions'])
        self.assertEqual(len(report['abstentions']),2)
        for p in report['protected_spans']:
            self.assertEqual(text[p['start']:p['end']],p['text'])

    def test_K17_U04_and_probabilistic_message(self):
        for key in ['K17','U04']:
            result=self.shifts(SAMPLES[key])
            self.assertEqual(len(result),1,key)
            self.assertIn('احتمالی',result[0]['reason'])
            self.assertEqual(result[0]['attribution'],'requires_context_review')
            for e in result[0]['evidence']:
                self.assertEqual(SAMPLES[key][e['start']:e['end']],e['evidence'])

    def test_finite_variants_not_just_regression_strings(self):
        text='شما پادکست را گوش دهید؛ تو پاسخت را در بخش نظرات بنویس.'
        self.assertEqual(len(self.shifts(text)),1)
        text='شما نشانی را یادداشت کنید؛ تو کارتت را نگه دار.'
        self.assertEqual(len(self.shifts(text)),1)

    def test_quotes_and_explicit_audience_switches(self):
        for text in ['«'+SAMPLES['K17']+'»',
                     'شما فایل صوتی را گوش دهید. خطاب به کودک: تو رسیدت را نگه دار.',
                     'مشتری: شما نشانی را یادداشت کنید.\nپشتیبان: تو کارتت را نگه دار.',
                     'تو راهرو بمان؛ شما نشانی را یادداشت کنید.']:
            self.assertFalse(self.shifts(text),text)


class CLIContracts(unittest.TestCase):
    def test_versions_sources_and_no_apply(self):
        for flags,version in [(['--json'],1),(['--simplify','--json'],2)]:
            text=SAMPLES['U05']
            r=subprocess.run([sys.executable,'-B',str(HUMAN/'persian_rewrite.py'),'-',*flags],input=text.encode(),capture_output=True,cwd='/tmp')
            self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads(r.stdout)
            self.assertEqual(result['schema_version'],version)
            self.assertEqual(result['source_text'],text)
            self.assertFalse(result['suggestions'])
        r=subprocess.run([sys.executable,'-B',str(HUMAN/'persian_rewrite.py'),'-','--apply'],input=b'',capture_output=True)
        self.assertEqual(r.returncode,2)

    def test_input_file_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.txt';data=(SAMPLES['V02']+'\r\n'+SAMPLES['K10']).encode();path.write_bytes(data)
            before=path.stat().st_mtime_ns
            r=subprocess.run([sys.executable,'-B',str(HUMAN/'persian_rewrite.py'),str(path),'--simplify','--json'],capture_output=True,cwd='/tmp')
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(path.read_bytes(),data)
            self.assertEqual(path.stat().st_mtime_ns,before)
            self.assertEqual(list(Path(tmp).iterdir()),[path])
            result=json.loads(r.stdout)
            self.assertEqual(result['source_text'],data.decode())
            self.assertFalse(result['simplification']['suggestions'])


if __name__=='__main__': unittest.main()
