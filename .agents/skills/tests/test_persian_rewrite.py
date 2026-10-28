"""Offline suggestion invariants, protection and CLI contracts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HUMAN = Path(__file__).resolve().parents[1] / 'ig-human'
sys.path.insert(0, str(HUMAN))
from persian_rewrite import suggest
from persian_protection import protected_spans
from persian_rewrite_checks import validate, mark_conflicts, validate_selection


class RewriteTests(unittest.TestCase):
    def test_extra_space(self):
        report = suggest('سلام  دوستان')
        self.assertEqual([(s['start'], s['end'], s['before'], s['replacement']) for s in report['suggestions']], [(4, 6, '  ', ' ')])

    def test_limited_zwnj(self):
        self.assertEqual(suggest('من می توانم پاسخ بدهم.')['suggestions'][0]['replacement'], 'می‌توانم')
        for text in ['من می‌توانم پاسخ بدهم.', 'سلام دوستان', 'Hello  world', 'می توانی', 'می توانمند', 'نامی توانم']:
            self.assertEqual(suggest(text)['suggestions'], [], text)

    def test_multiple_occurrences(self):
        report = suggest('سلام  دوستان؛ من می خواهم پاسخ بدهم. سلام  دوستان')
        self.assertEqual(len(report['suggestions']), 3)
        self.assertEqual([s['id'] for s in report['suggestions']], ['s1', 's2', 's3'])

    def test_source_hash_and_offsets(self):
        text = '😀 مُحتوا\r\nسلام  دوستان؛ می خواهم بخوانم.'
        report = suggest(text)
        self.assertEqual(report['source_text'], text)
        self.assertEqual(report['source_sha256'], hashlib.sha256(text.encode()).hexdigest())
        for item in report['suggestions'] + report['abstentions']:
            self.assertEqual(text[item['start']:item['end']], item['before'])
        for span in report['protected_spans']:
            self.assertEqual(text[span['start']:span['end']], span['text'])

    def test_user_protection_all_occurrences_and_overlap(self):
        text = 'برند  نو؛ برند  نو؛ سلام  دوستان'
        result = suggest(text, ['برند  نو', 'نو'])
        self.assertEqual(len(result['suggestions']), 1)
        self.assertEqual(len(result['abstentions']), 2)
        self.assertEqual(sum(s['reason'] == 'user_protected' for s in result['protected_spans']), 4)
        self.assertEqual(result['options'], {'protect': ['برند  نو', 'نو']})

    def test_quotes(self):
        for left, right in [('«', '»'), ('“', '”'), ('‘', '’'), ('"', '"'), ("'", "'")]:
            result = suggest(left + 'سلام  دوستان؛ می توانم' + right)
            self.assertFalse(result['suggestions'])
            self.assertTrue(result['abstentions'])
        for text in ['«سلام  دوستان', '«او گفت “سلام  دوستان” و رفت»']:
            self.assertFalse(suggest(text)['suggestions'])

    def test_dialogue_and_reported_speech(self):
        for text in ['مشتری: سلام  دوستان\nپشتیبان: می توانم کمک کنم.', 'او گفت سلام  دوستان.', 'او نوشت می توانم بیایم.']:
            self.assertFalse(suggest(text)['suggestions'])

    def test_sensitive_clauses(self):
        for text in ['این  رایگان نیست.', 'اگر سلام  دوستان را گفتید، ادامه دهید.', 'شاید می توانم بیایم.', 'شما می توانید بخوانید.', 'تو  انتخاب کن.', 'بدون  هزینه', 'فقط  امروز', 'نمی خواهم  بروم', 'این نتیجه  تضمینی است.', 'حداقل  هزینه', 'احتمالاً می رود.', 'این  قطعی است.', 'همه  خوشحالند.']:
            self.assertFalse(suggest(text)['suggestions'], text)
        report = suggest('اگر این  شد، ادامه دهید. سلام  دوستان')
        self.assertEqual(len(report['suggestions']), 1)

    def test_ambiguous_layout(self):
        for text in ['  سلام  دوستان', 'سلام\t دوستان', '- سلام  دوستان', 'سلام  | دوستان', 'سلام\u202e  دوستان', '`سلام  دوستان`', '```\nسلام  دوستان\n```']:
            self.assertFalse(suggest(text)['suggestions'], text)
        self.assertFalse(suggest('سلام\n\nدوستان')['suggestions'])

    def test_numbers_and_links_preserved_in_preview(self):
        text = 'سلام  دوستان؛ قیمت ۱٬۲۵۰٬۰۰۰ تومان؛ ۳۰٪؛ https://example.com/p?id=۱۲&x=a'
        report = suggest(text)
        preview = text
        for item in reversed(report['suggestions']):
            preview = preview[:item['start']] + item['replacement'] + preview[item['end']:]
        self.assertEqual(preview, text.replace('سلام  دوستان', 'سلام دوستان'))
        for span in report['protected_spans']:
            self.assertIn(span['text'], preview)

    def test_determinism_no_score_no_rewrite(self):
        text = 'سلام  دوستان'
        a = suggest(text)
        self.assertEqual(a, suggest(text))
        self.assertFalse({'score', 'confidence', 'rewritten_text', 'human_score'} & a.keys())
        self.assertTrue(all(s['requires_confirmation'] for s in a['suggestions']))
        self.assertEqual(a['suggestions'][0]['checks']['semantic_review'], 'required')

    def test_conflicts_and_invalid_selections(self):
        items = [dict(id='s1', start=0, end=4), dict(id='s2', start=3, end=5), dict(id='s3', start=5, end=7)]
        mark_conflicts(items)
        self.assertEqual(items[0]['conflicts_with'], ['s2'])
        self.assertTrue(validate_selection(items, ['s1', 's3']))
        for selection in [['s1', 's2'], ['bad'], ['s1', 's1']]:
            with self.assertRaises(ValueError): validate_selection(items, selection)

    def test_mechanical_idempotence_in_test_preview(self):
        text = 'سلام  دوستان؛ من می توانم پاسخ بدهم.'
        report = suggest(text)
        preview = text
        for item in reversed(report['suggestions']):
            preview = preview[:item['start']] + item['replacement'] + preview[item['end']:]
        self.assertFalse(suggest(preview)['suggestions'])
        self.assertEqual(text, report['source_text'])

    def test_protected_candidate_validation(self):
        text = 'می توانم'
        c = dict(start=0, end=len(text), before=text, replacement='می‌توانم', rule_id='fa-limited-zwnj')
        self.assertEqual(validate(text, c, protected_spans(text, [text])), 'protected_or_ambiguous_span')
        self.assertIsNone(validate(text, c, []))
        c['replacement'] = 'میتوانم'
        self.assertEqual(validate(text, c, []), 'invalid_zwnj_change')

    def test_literal_protection_not_regex(self):
        text = 'نام  (نو)+ نام  (نو)+'
        report = suggest(text, ['نام  (نو)+'])
        self.assertFalse(report['suggestions'])
        self.assertEqual(sum(s['reason'] == 'user_protected' for s in report['protected_spans']), 2)

    def test_invalid_candidate_is_rejected(self):
        c = dict(start=0, end=2, before='نه', replacement='بله', rule_id='fa-limited-zwnj')
        self.assertEqual(validate('نه', c, []), 'non_mechanical_change')
        c['before'] = 'خیر'
        self.assertEqual(validate('نه', c, []), 'invalid_source_span')
        with self.assertRaises(ValueError): suggest('سلام', [''])


PROTECTION_CASES = [
 ('url', 'https://example.com/a?x=۱۲&y=test'),
 ('url', 'www.example.com/a'),
 ('email', 'name+test@example.com'),
 ('hashtag', '#می‌خواهم_بسازم'),
 ('mention', '@brand.name'),
 ('number', '۱۲۳۴'), ('number', '1234'), ('number', '١٢٣٤'),
 ('number', '۱٬۲۵۰٬۰۰۰ تومان'), ('number', '۳٫۵٪'), ('number', '30%'),
 ('number', '۱۴۰۵/۰۸/۱۰'), ('number', '۱۸:۳۰'),
 ('latin_or_code', 'SKU-AB12'), ('latin_or_code', 'CapCut'),
 ('latin_or_code', 'Export 1080p'), ('quotation', '«می توانم»'),
]


def protection_case(reason, value):
    def test(self):
        text = 'سلام  دوستان؛ ' + value
        report = suggest(text)
        matching = [s for s in report['protected_spans'] if s['reason'] == reason]
        self.assertTrue(any(s['text'] == value for s in matching), (reason, value, matching))
        for s in matching:
            self.assertEqual(text[s['start']:s['end']], s['text'])
    return test


for index, (reason, value) in enumerate(PROTECTION_CASES):
    setattr(RewriteTests, f'test_protection_{index:02}', protection_case(reason, value))


class RewriteCLI(unittest.TestCase):
    def run_cli(self, *args, data=b''):
        return subprocess.run([sys.executable, '-B', str(HUMAN/'persian_rewrite.py'), *args], input=data, capture_output=True, cwd='/tmp')

    def test_stdin(self):
        text = '😀 سلام  دوستان\r\nمی توانم پاسخ بدهم.'
        result = self.run_cli('-', '--json', data=text.encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['source_text'], text)

    def test_file_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'input.txt'
            data = 'سلام  دوستان\r\nمی توانم پاسخ بدهم.'.encode()
            p.write_bytes(data)
            before = p.stat()
            result = self.run_cli(str(p), '--json')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(p.read_bytes(), data)
            self.assertEqual(p.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(json.loads(result.stdout)['source_sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(list(Path(tmp).iterdir()), [p])

    def test_protect_and_text(self):
        result = self.run_cli('-', '--json', '--protect', 'برند  نو', data='برند  نو'.encode())
        report = json.loads(result.stdout)
        self.assertFalse(report['suggestions'])
        self.assertTrue(report['abstentions'])
        result = self.run_cli('-', data='سلام  دوستان'.encode())
        self.assertEqual(result.returncode, 0)
        self.assertIn('هیچ تغییری اعمال نشده', result.stdout.decode())

    def test_errors_and_no_apply(self):
        for args in [('--apply',), ('--format', 'reel'), ('--protect', '')]:
            self.assertEqual(self.run_cli(*args).returncode, 2)
        self.assertEqual(self.run_cli('/nonexistent/input.txt').returncode, 1)
        self.assertEqual(self.run_cli('-', data=b'\xff').returncode, 1)

    def test_english_empty_and_schema(self):
        for text in ['', 'Hello  world', 'سلام دوستان']:
            result = self.run_cli('--json', data=text.encode())
            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertFalse(report['suggestions'])
            self.assertEqual(report['source_text'], text)
            self.assertTrue({'schema_version','source_text','source_sha256','options','suggestions','protected_spans','abstentions','limitations'} <= report.keys())


if __name__ == '__main__':
    unittest.main()
