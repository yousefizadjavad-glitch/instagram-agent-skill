"""Run: python3 -B -m unittest discover -s .agents/skills/tests -v"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / '.agents/skills'
sys.path.insert(0, str(CORE))
from text_core import SENT_RE, normalize_numbers, valid_zwnj, words


def load(base, folder, name):
    sys.path.insert(0, str(base / folder))
    spec = importlib.util.spec_from_file_location(base.name + folder + name, base / folder / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = load(CORE, 'ig-human', 'humanize')
D = load(CORE, 'ig-human', 'detect')
K = load(CORE, 'ig-reel', 'hookscore')
B = load(CORE, 'ig-reel', 'beats')
LEX = H.load_lexicon()


class PersianCoreTests(unittest.TestCase):
    def test_preserve_valid_zwnj(self):
        for text in ['می‌خواهم این ۳ اشتباه را تکرار نکنم.', 'می‌روم؟ نمی‌روم؟ چرا؟', 'خانه‌ها', 'میِ‌روم']:
            self.assertEqual(H.humanize(text, LEX)[0].strip(), text)
            self.assertEqual(D.check_fingerprint(text)[0], 100)

    def test_reject_invalid_zwnj(self):
        for text in ['a‌b', '‌می', 'می‌', 'می‌‌روم', '۳‌۴', 'می‌ رود']:
            self.assertNotIn('\u200c', H.humanize(text, LEX)[0])
            self.assertLess(D.check_fingerprint(text)[0], 100)

    def test_other_format_characters(self):
        for c in ['\u200b', '\u200d', '\u202e', '\u2066', '\ufeff', '\u00ad']:
            text = 'می' + c + 'روم'
            self.assertNotIn(c, H.humanize(text, LEX)[0])
            self.assertLess(D.check_fingerprint(text)[0], 100)

    def test_no_new_valid_joiner_after_cleanup(self):
        for text in ['می\u200c\u202eروم', 'می\u200b\u200cروم']:
            self.assertNotIn('\u200c', H.humanize(text, LEX)[0])

    def test_persian_counts(self):
        text = 'می‌خواهم این ۳ اشتباه را تکرار نکنم.'
        self.assertEqual([len(m.words(text)) for m in (D, K, B)], [6, 7, 7])
        self.assertAlmostEqual(B.analyse(text)['total_seconds'], 2.55)

    def test_mixed_counts(self):
        text = 'این 3 نکته برای Reel مهم است.'
        self.assertEqual([len(m.words(text)) for m in (D, K, B)], [6, 7, 7])
        self.assertEqual(B.analyse(text)['total_seconds'], 2.55)

    def test_question_boundaries(self):
        text = 'می‌روم؟ نمی‌روم؟ چرا؟'
        self.assertEqual(len(SENT_RE.findall(text)), 3)
        self.assertEqual([len(m.words(text)) for m in (D, K, B)], [3, 3, 3])
        self.assertEqual(B.analyse(text)['total_seconds'], 1.09)
        self.assertEqual(len(D.sentences('چرا این کار را می‌کنید؟ آیا راه دیگری ندارید؟ حالا چه باید بکنیم؟')), 3)

    def test_long_paragraph_splits_at_persian_question(self):
        text = 'چرا این ۳ اشتباه را تکرار می‌کنید؟ ' * 4
        beats = B.split_beats(text, 165 / 60)
        self.assertEqual(len(beats), 4)
        self.assertTrue(all(b.endswith('؟') for b in beats))

    def test_digit_equivalence(self):
        for template in [('این {0} نکته مهم است. ' * 7), 'این {} نکته مهم است.', 'Stop these {} Reel mistakes.', 'You saved ${} today.']:
            variants = [template.format(n) for n in ['3', '۳', '٣']]
            for m in (D, K, B):
                self.assertEqual(m.words(variants[0]), m.words(variants[1]))
                self.assertEqual(m.words(variants[0]), m.words(variants[2]))
            self.assertEqual(K.run(variants[0]), K.run(variants[1]))
            self.assertEqual(K.run(variants[0]), K.run(variants[2]))
            self.assertEqual(D.run(variants[0], LEX), D.run(variants[1], LEX))
            self.assertEqual(B.analyse(variants[0])['beats'][0]['concrete'], B.analyse(variants[2])['beats'][0]['concrete'])

    def test_numeric_separators(self):
        self.assertEqual(normalize_numbers('۱۲٬۳۴۵٫۶٪'), '12,345.6%')
        self.assertEqual(normalize_numbers('١٢٬٣٤٥٫٦٪'), '12,345.6%')
        for n in ['12,345.6%', '۱۲٬۳۴۵٫۶٪', '١٢٬٣٤٥٫٦٪']:
            self.assertEqual(K.words(n), K.words('12,345.6%'))
            self.assertEqual(K.check_specificity(n), K.check_specificity('12,345.6%'))

    def test_combining_marks_and_boundaries(self):
        self.assertEqual(words('مُحتوا می‌روم Reel'), ['مُحتوا', 'می‌روم', 'Reel'])
        self.assertEqual(words('این،متن؛خوب؟'), ['این', 'متن', 'خوب'])
        self.assertEqual(words('abc‌def'), ['abc', 'def'])
        self.assertEqual(words('cafe\u0301 हिन्दी'), ['cafe\u0301', 'हिन्दी'])

    def test_digit_normalization_does_not_change_output(self):
        text = 'این ۳ نکته برای Reel مهم است.'
        self.assertEqual(H.humanize(text, LEX)[0].strip(), text)
        self.assertEqual(B.analyse(text)['beats'][0]['text'], text)

    def test_english_regression_against_original(self):
        old = {name: load(ROOT / 'skills', folder, name) for folder, name in [('ig-human', 'humanize'), ('ig-human', 'detect'), ('ig-reel', 'hookscore'), ('ig-reel', 'beats')]}
        examples = ["I don't want you to waste 30 minutes on a script. You can start with a useful example, explain what changed, and show the result before asking anyone to save it.", "Don't waste your time. Show a useful example first.", 'Stop these 3 Reel mistakes.', 'I lost $18,000 on one missing contract.', 'Hello everyone! In this video I will show you how.', 'A 30-second Reel takes 5 minutes.', 'Steal this 3-point checklist before your next Reel.', "You're paying $12.50 for this tool.", 'First line.\nSecond line?\nSave this line.', 'We use a robust system — it works seamlessly.', 'Visit https://example.com/a?q=3 and email a@b.com.']
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(H.humanize(text, LEX), old['humanize'].humanize(text, LEX))
                self.assertEqual(D.run(text, LEX), old['detect'].run(text, LEX))
                self.assertEqual(K.run(text), old['hookscore'].run(text))
                self.assertEqual(B.analyse(text, target=30), old['beats'].analyse(text, target=30))

    def test_cli_from_other_directory(self):
        text = 'می‌روم؟ نمی‌روم؟ چرا؟'
        for folder, name in [('ig-human', 'humanize'), ('ig-human', 'detect'), ('ig-reel', 'hookscore'), ('ig-reel', 'beats')]:
            result = subprocess.run([sys.executable, '-B', str(CORE / folder / (name + '.py')), '-', '--json'], input=text, text=True, capture_output=True, cwd='/tmp')
            self.assertEqual(result.returncode, 0, result.stderr)
            json.loads(result.stdout)


if __name__ == '__main__':
    unittest.main()
