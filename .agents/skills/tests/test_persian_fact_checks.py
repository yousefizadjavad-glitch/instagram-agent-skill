"""Bounded explicit fact checks and workflow decision input safety."""
import sys
import json
import subprocess
import tempfile
from pathlib import Path
import unittest
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from persian_workflow import coordinate


def request(text, facts=None, protect=None):
    return dict(format='caption',topic='محصول',goal='معرفی',audience='خریداران',
        target_tone='semi-formal',target_address='unspecified',verified_facts=facts or [],
        protected_terms=protect or [],optional_cta=None,draft={'text':text})


class FactChecks(unittest.TestCase):
    def facts(self,text,facts,protect=None):
        return coordinate(request(text,facts,protect))['fact_checks']

    def test_price_conflict(self):
        r=self.facts('قیمت: ۹۸۰٬۰۰۰ تومان',['قیمت: ۴۸۰٬۰۰۰ تومان'])
        self.assertEqual(len(r['mismatches']),1)
        self.assertEqual(r['status'],'needs_review')

    def test_digits_and_grouping(self):
        for value in ['480000','480,000','۴۸۰٬۰۰۰','٤٨٠٬٠٠٠','۴۸۰۰۰۰٫۰']:
            with self.subTest(value=value):
                r=self.facts('قیمت: '+value+' تومان',['قیمت: ۴۸۰٬۰۰۰ تومان'])
                self.assertEqual(r['fact_checks'][0]['status'],'matched_explicit_value')

    def test_weight_not_price(self):
        r=self.facts('قیمت: ۴۸۰٬۰۰۰ تومان؛ وزن: ۹۸۰ گرم',['۴۸۰٬۰۰۰ تومان'])
        self.assertFalse(r['mismatches']);self.assertFalse(r['ambiguous'])

    def test_only_weight_missing_price(self):
        r=self.facts('وزن: ۹۸۰ گرم',['۴۸۰٬۰۰۰ تومان'])
        self.assertFalse(r['fact_checks'])

    def test_currency_not_converted(self):
        r=self.facts('۴۸۰۰۰۰ ریال',['۴۸۰۰۰۰ تومان'])
        self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_bare_numbers_no_comparison(self):
        self.assertFalse(self.facts('۹۸۰',['۴۸۰'])['fact_checks'])

    def test_multiple_prices(self):
        for text,facts in [('۴۸۰ تومان و ۹۸۰ تومان',['۴۸۰ تومان']),('۹۸۰ تومان',['۴۸۰ تومان','۹۸۰ تومان'])]:
            r=self.facts(text,facts);self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_multiple_products(self):
        r=self.facts('نام محصول: ماگ؛ قیمت: ۹۸۰ تومان؛ نام محصول: کاسه',['نام محصول: ماگ','۴۸۰ تومان'],['ماگ'])
        self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_sensitive_context(self):
        for text in ['قیمت ۹۸۰ تومان نیست.','اگر قیمت ۹۸۰ تومان باشد.','شاید ۹۸۰ تومان','«۹۸۰ تومان»','قیمت قبلی ۹۸۰ تومان']:
            with self.subTest(text=text):
                r=self.facts(text,['۴۸۰ تومان']);self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_price_role_ambiguity(self):
        for text in ['هزینه ارسال: ۹۸۰ تومان','قیمت کاسه: ۹۸۰ تومان']:
            r=self.facts(text,['قیمت ماگ: ۴۸۰ تومان'])
            self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_date_normalization(self):
        r=self.facts('تاریخ: 1405-8-6',['تاریخ: ۱۴۰۵/۰۸/۰۶'])
        self.assertEqual(r['fact_checks'][0]['status'],'matched_explicit_value')

    def test_date_conflict(self):
        self.assertTrue(self.facts('تاریخ: ۱۴۰۵/۰۸/۰۷',['تاریخ: ۱۴۰۵/۰۸/۰۶'])['mismatches'])

    def test_date_role_uncertain(self):
        r=self.facts('تاریخ تولید: ۱۴۰۵/۰۸/۰۷',['تاریخ تحویل: ۱۴۰۵/۰۸/۰۶'])
        self.assertTrue(r['ambiguous']);self.assertFalse(r['mismatches'])

    def test_dates_not_inferred(self):
        self.assertFalse(self.facts('فردا',['امروز'])['fact_checks'])

    def test_code_normalization(self):
        r=self.facts('کد محصول: AB-12',['کد محصول: AB-۱۲'])
        self.assertEqual(r['fact_checks'][0]['status'],'matched_explicit_value')

    def test_code_conflict(self):
        self.assertTrue(self.facts('کد محصول: AB-13',['کد محصول: AB-12'])['mismatches'])

    def test_unlabelled_code(self):
        self.assertFalse(self.facts('AB-13',['AB-12'])['fact_checks'])

    def test_explicit_protected_name(self):
        r=self.facts('برند: ماه نقره‌ای',['برند: ماه  نقره‌ای'],['ماه  نقره‌ای'])
        self.assertTrue(r['mismatches'])

    def test_name_exact_match(self):
        r=self.facts('برند: ماه  نقره‌ای',['برند: ماه  نقره‌ای'],['ماه  نقره‌ای'])
        self.assertEqual(r['fact_checks'][0]['status'],'matched_explicit_value')

    def test_unprotected_name_not_guessed(self):
        self.assertFalse(self.facts('برند: ب',['برند: الف'])['fact_checks'])

    def test_protected_term_not_inferred_brand(self):
        self.assertFalse(self.facts('برند: ب',[],['الف'])['fact_checks'])

    def test_omission_not_conflict(self):
        r=self.facts('امروز سفال داریم.',['۴۸۰ تومان','تاریخ: ۱۴۰۵/۰۸/۰۶','کد محصول: A-1','برند: الف'],['الف'])
        self.assertEqual(r['status'],'not_checked');self.assertFalse(r['mismatches'])

    def test_url_numbers_not_dates(self):
        r=self.facts('https://example.com/1405/08/07',['تاریخ: ۱۴۰۵/۰۸/۰۶'])
        self.assertFalse(r['fact_checks'])

    def test_evidence_and_hashes(self):
        req=request('قیمت: ۹۸۰ تومان',['قیمت: ۴۸۰ تومان']);before=deepcopy(req);r=coordinate(req)
        self.assertEqual(req,before);self.assertFalse(r['applied'])
        for item in r['fact_checks']['fact_checks']:
            self.assertEqual(item['section_id'],'caption.text')
            self.assertEqual(item['source_hash'],r['sections'][0]['source_hash'])
            for evidence in item['observed']:
                self.assertEqual(req['draft']['text'][evidence['start']:evidence['end']],evidence['before'])

    def test_decision_type_errors(self):
        req=request('امروز  سفال داریم.');r=coordinate(req);s=r['suggestions'][0]
        d=dict(section_id=s['section_id'],suggestion_id=s['id'],source_hash=s['source_hash'],request_hash=r['source_hash'],start=s['start'],end=s['end'],before=s['before'],action='accept')
        for key in ['section_id','suggestion_id','source_hash','request_hash','before','action']:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,f'decision.{key} must be a string'):
                    coordinate(req,[dict(d,**{key:[]})])

    def test_cli_files_and_error(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.json';dp=Path(td)/'decisions.json'
            raw=json.dumps(request('امروز  سفال داریم.')).encode();p.write_bytes(raw)
            dp.write_text(json.dumps([dict(section_id=[],suggestion_id='x',source_hash='x',request_hash='x',start=0,end=1,before='x',action='accept')]))
            before=dp.read_bytes()
            result=subprocess.run([sys.executable,str(ROOT/'persian_workflow.py'),str(p),'--decisions',str(dp)],capture_output=True)
            self.assertEqual(result.returncode,2);self.assertIn(b'decision.section_id must be a string',result.stderr)
            self.assertFalse(result.stdout);self.assertEqual(raw,p.read_bytes());self.assertEqual(before,dp.read_bytes())

    def test_e2e_three_formats(self):
        for fmt,draft in [('caption',{'text':'قیمت: ۹۸۰ تومان؛ امروز  سفال داریم.'}),('reel',dict(hook='امروز  سفال داریم.',spoken_script='قیمت: ۹۸۰ تومان',on_screen_text='ماگ',ending='پایان.')),('story',{'cards':[{'number':1,'text':'شما سفارش را ثبت کنید.'},{'number':2,'text':'تو هزینه را پرداخت کن.'},{'number':3,'text':'قیمت: ۹۸۰ تومان'}]})]:
            with self.subTest(fmt=fmt):
                req=request('', ['۴۸۰ تومان']);req.update(format=fmt,draft=draft)
                p=subprocess.run([sys.executable,str(ROOT/'persian_workflow.py'),'-'],input=json.dumps(req).encode(),capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
                self.assertEqual(len(r['fact_checks']['mismatches']),1);self.assertFalse(r['applied'])
                if fmt=='story':self.assertTrue(r['sequence_review']['findings'])


if __name__=='__main__': unittest.main()
