"""Workflow boundaries and immutable, explicitly versioned decisions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from persian_workflow import coordinate, decisions_for


def brief(fmt='caption', draft=None):
    return dict(format=fmt, topic='سفال', goal='معرفی', audience='علاقه‌مندان',
                target_tone='semi-formal', target_address='unspecified', verified_facts=[],
                protected_terms=[], optional_cta=None, draft=draft)


def decision(report, index=0, action='accept'):
    s = report['suggestions'][index]
    return dict(section_id=s['section_id'], suggestion_id=s['id'], source_hash=s['source_hash'],
                request_hash=report['source_hash'], start=s['start'], end=s['end'], before=s['before'], action=action)


class WorkflowTests(unittest.TestCase):
    def test_brief_only_three_formats(self):
        for fmt in ('caption','reel','story'):
            with self.subTest(fmt=fmt):
                r=coordinate(brief(fmt))
                self.assertEqual(r['mode'],'brief_only')
                self.assertFalse(r['generation_instruction']['generated_draft'])
                self.assertEqual(r['sections'],[])

    def test_caption_exact_source_offsets_emoji_crlf(self):
        text='🌿\r\nامروز  سفال داریم.'
        req=brief(draft={'text':text}); original=deepcopy(req)
        r=coordinate(req); s=r['sections'][0]
        self.assertEqual(req,original)
        self.assertEqual(s['source_text'],text)
        self.assertEqual(s['source_hash'],hashlib.sha256(text.encode()).hexdigest())
        self.assertTrue(s['suggestions'])
        for suggestion in s['suggestions']:
            self.assertEqual(text[suggestion['start']:suggestion['end']],suggestion['before'])
        self.assertFalse(r['applied'])

    def test_reel_separate_sections(self):
        draft={k:'امروز  سفال داریم.' for k in ('hook','spoken_script','on_screen_text','ending')}
        r=coordinate(brief('reel',draft))
        self.assertEqual(len(r['sections']),4)
        self.assertEqual(len({s['id'] for s in r['suggestions']}),len(r['suggestions']))
        self.assertNotIn('sequence_review',r)

    def test_story_mapping_shift(self):
        texts=['شما سفارش را ثبت کنید.','تو هزینه را پرداخت کن.']
        req=brief('story',{'cards':[dict(number=i,text=t) for i,t in enumerate(texts,1)]})
        r=coordinate(req); sequence=r['sequence_review']
        self.assertEqual(sequence['source_text'],'\n'.join(texts))
        shifts=[f for f in sequence['findings'] if f['rule_id']=='fa-address-shift']
        self.assertEqual(len(shifts),1)
        for evidence in shifts[0]['evidence']:
            for ref in evidence['section_spans']:
                section=next(s for s in r['sections'] if s['section_id']==ref['section_id'])
                self.assertEqual(section['source_text'][ref['start']:ref['end']],evidence['evidence'])

    def test_story_quote_and_audience_exception(self):
        for texts in [('«شما سفارش را ثبت کنید.»','«تو هزینه را پرداخت کن.»'),
                      ('شما سفارش را ثبت کنید.','خطاب به دوست عزیز: تو هزینه را پرداخت کن.')]:
            r=coordinate(brief('story',{'cards':[dict(number=i,text=t) for i,t in enumerate(texts,1)]}))
            self.assertFalse(r['sequence_review']['findings'])

    def test_protected_names_facts_numbers_urls(self):
        req=brief(draft={'text':'ماه  نقره‌ای؛ امروز  سفال داریم. قیمت ۴۸۰٬۰۰۰ تومان https://example.com/a 2026/10/28'})
        req['protected_terms']=['ماه  نقره‌ای']; req['verified_facts']=['امروز  سفال داریم.']
        r=coordinate(req)
        self.assertFalse(r['suggestions'])
        self.assertTrue(r['abstentions'])
        self.assertEqual(r['sections'][0]['source_text'],req['draft']['text'])

    def test_four_raw_contracts(self):
        from persian_review import review
        from persian_tone import review_tone
        from persian_rewrite import suggest
        from persian_simplify import simplify
        text='در خصوص سفارش توضیح دهید.'
        r=coordinate(brief(draft={'text':text}))
        raw=r['sections'][0]['raw_reports']
        self.assertEqual(raw['persian_review'],review(text))
        self.assertEqual(raw['persian_tone'],review_tone(text,'semi-formal','unspecified'))
        self.assertEqual(raw['persian_rewrite'],suggest(text,[]))
        self.assertEqual(raw['persian_simplify'],simplify(text,[],'semi-formal'))
        self.assertEqual(raw['persian_rewrite']['schema_version'],1)

    def test_natural_no_suggestions(self):
        r=coordinate(brief(draft={'text':'امروز کاسه ساختم.'}))
        self.assertEqual(r['suggestions'],[])
        self.assertTrue(r['limitations'])
        self.assertTrue(any(a['reason']=='insufficient_evidence' for a in r['abstentions']))

    def test_negation_linguistic_abstention(self):
        r=coordinate(brief(draft={'text':'در خصوص ارسال سفارش اطلاع ندارم.'}))
        self.assertFalse([s for s in r['suggestions'] if s['tool']=='persian_simplify'])
        self.assertTrue(r['abstentions'])

    def test_explicit_accept_reject_no_application(self):
        req=brief(draft={'text':'امروز  سفال داریم و فردا  کاسه می‌سازیم.'})
        r=coordinate(req)
        decisions=[decision(r,0),decision(r,1,'reject')]
        updated=coordinate(req,decisions)
        self.assertEqual([x['action'] for x in updated['decisions']],['accept','reject'])
        self.assertTrue(all(not x['applied'] for x in updated['decisions']))
        self.assertEqual(updated['sections'][0]['source_text'],req['draft']['text'])

    def test_stale_text(self):
        req=brief(draft={'text':'امروز  سفال داریم.'}); r=coordinate(req)
        req['draft']['text']='فردا  سفال داریم.'
        with self.assertRaises(ValueError): coordinate(req,[decision(r)])

    def test_stale_brief(self):
        req=brief(draft={'text':'امروز  سفال داریم.'}); r=coordinate(req)
        req['audience']='هنرمندان'
        with self.assertRaises(ValueError): coordinate(req,[decision(r)])

    def test_invalid_decision_fields(self):
        req=brief(draft={'text':'امروز  سفال داریم.'}); r=coordinate(req)
        for key,val in [('before','bad'),('start',False),('end',999),('action','apply'),
                        ('source_hash','x'),('suggestion_id','unknown'),('section_id','unknown')]:
            with self.subTest(key=key):
                d=decision(r); d[key]=val
                with self.assertRaises(ValueError): coordinate(req,[d])

    def test_duplicate_decision(self):
        r=coordinate(brief(draft={'text':'امروز  سفال داریم.'}))
        with self.assertRaises(ValueError): decisions_for(r,[decision(r),decision(r)])

    def test_overlap_refused(self):
        r=coordinate(brief(draft={'text':'امروز  سفال داریم.'}))
        item=deepcopy(r['sections'][0]['suggestions'][0]); item['id']='overlap'
        r['sections'][0]['suggestions'].append(item)
        d=decision(r); other=dict(d,suggestion_id='overlap')
        with self.assertRaises(ValueError): decisions_for(r,[d,other])

    def test_request_validation(self):
        for key,val in [('format','video'),('target_tone','friendly'),('target_address','you'),
                        ('topic',''),('goal',None),('audience',[]),('verified_facts','x'),
                        ('protected_terms',['']),('optional_cta',False),('unknown','x')]:
            with self.subTest(key=key):
                req=brief(); req[key]=val
                with self.assertRaises(ValueError): coordinate(req)
        req=brief(); del req['topic']
        with self.assertRaises(ValueError): coordinate(req)

    def test_draft_validation(self):
        cases=[('caption',{'text':''}),('caption','text'),('caption',{'text':'متن','extra':1}),
               ('reel',{'hook':'متن'}),('story',{'cards':[]}),
               ('story',{'cards':[{'number':2,'text':'متن'}]}),
               ('story',{'cards':[{'number':True,'text':'متن'}]}),
               ('story',{'cards':[{'number':1,'text':5}]})]
        for fmt,draft in cases:
            with self.subTest(fmt=fmt,draft=draft):
                with self.assertRaises(ValueError): coordinate(brief(fmt,draft))

    def run_cli(self, raw, *args):
        return subprocess.run([sys.executable,str(ROOT/'persian_workflow.py'),*args],
            input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd='/tmp')

    def test_cli_stdin_json(self):
        p=self.run_cli(json.dumps(brief(draft={'text':'Hello فارسی 🌿'}),ensure_ascii=False).encode())
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['sections'][0]['source_text'],'Hello فارسی 🌿')

    def test_cli_input_file_immutable_and_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'brief.json'; ds=Path(tmp)/'decisions.json'
            req=brief(draft={'text':'امروز  سفال داریم.'})
            raw=json.dumps(req,ensure_ascii=False).encode(); path.write_bytes(raw)
            r=coordinate(req); ds.write_text(json.dumps([decision(r)]))
            original=ds.read_bytes()
            p=self.run_cli(b'',str(path),'--decisions',str(ds))
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(path.read_bytes(),raw); self.assertEqual(ds.read_bytes(),original)
            self.assertEqual(json.loads(p.stdout)['decisions'][0]['action'],'accept')

    def test_cli_errors(self):
        for raw in (b'{', b'\xff', b'[]', b'{"format":"caption","format":"story"}', b'null'):
            with self.subTest(raw=raw):
                p=self.run_cli(raw); self.assertEqual(p.returncode,2); self.assertFalse(p.stdout)
        self.assertEqual(self.run_cli(b'','/missing/brief.json').returncode,2)
        self.assertEqual(self.run_cli(b'','--apply').returncode,2)
        self.assertEqual(self.run_cli(b'','-','--decisions','-').returncode,2)


if __name__ == '__main__': unittest.main()
