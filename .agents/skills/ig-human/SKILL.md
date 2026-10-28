---
name: ig-human
description: >-
  Strip the machine fingerprint out of any draft - em dashes, AI slop words,
  invisible watermark characters - and score it against a five-check detection
  panel before it goes out. Use whenever text needs to sound human, when the
  user says humanize, "does this sound like AI", "remove the em dashes",
  "de-slop this", "this sounds like ChatGPT", or before any caption, script,
  comment, reply or DM is shown to the user.
---

## Codex execution

Run shell examples from the repository root. Resolve this skill's local data
files relative to this SKILL.md, not the shell working directory. Python 3 is
required for the bundled tools; they use only the standard library.

References such as `$ig-human` mean: load the sibling skill's SKILL.md and
follow it in the current task. If it is not in the active skill catalog, read
`.agents/skills/ig-human/SKILL.md` directly (substitute the referenced name).
Do not run skill names as shell commands. Keep the whole skill pack together
so sibling Python imports and JSON resources remain available.

Shared account context belongs in `/workspace/instagram-agent-data/`:
`voice.md`, `swipe.md`, `log.md`, and `plan.md`. This is a configurable working
convention, not an automatically synchronized Codex store. If the user chooses
another location, use it consistently across all skills. Create the directory
only when saving authorized output; preserve existing files and never store
credentials there. Use supplied voice instructions for a test without creating
a profile. Missing tools or source data must be reported, not invented.

Do not publish, send messages, or change Instagram account settings. Produce
content for the user to review and publish themselves.


# ig-human

## مسیر فارسی — مستقل از humanizer انگلیسی

ابتدا [بریف و گردش‌کار مشترک فارسی](../PERSIAN_WORKFLOW.md) را بخوانید. برای متن فارسی و بخش‌های فارسی متن ترکیبی، این بخش بر تمام دستورهای پاک‌سازی، امتیاز و حلقهٔ PASS پایین تقدم دارد. بخش پایین از «English path» به بعد مخصوص انگلیسی است؛ ابزارها و مثال‌های انگلیسی حفظ شده‌اند. `humanize.py` را برای فارسی اجرا نکنید؛ نیم‌فاصله، معنا و لحن نباید با پاک‌سازی انگلیسی دست‌کاری شوند.

فقط چهار ابزار فارسی موجود استفاده شوند: `persian_review` (یافته‌های سبکی)، `persian_tone` (لحن و خطاب احتمالی)، `persian_rewrite` (پیشنهاد مکانیکی محدود) و `persian_simplify` (پیشنهاد محدود زبانی/راهنمای انسانی). این‌ها قواعد آفلاین‌اند، نه تولیدکنندهٔ خلاق یا تضمین‌کنندهٔ کیفیت.

### قراردادهای موجود، بدون تغییر

از ریشهٔ مخزن، روی فایل UTF-8 همان نسخهٔ متن یا stdin اجرا کنید. `draft.txt` فقط نمونهٔ مسیر ورودی موجود است؛ برای بازبینی، فایل کاربر را تغییر ندهید.

```bash
# persian_review + persian_tone؛ مثالِ انتخاب کاربر: نیمه‌رسمی و شما
python3 .agents/skills/ig-human/detect.py draft.txt --lang fa --tone-check --target-tone semi-formal --target-address shoma --json
# persian_rewrite + persian_simplify؛ همان لحن و نام صریحاً محافظت‌شده
python3 .agents/skills/ig-human/persian_rewrite.py draft.txt --json --simplify --target-tone semi-formal --protect 'ماه  نقره‌ای'
```

مقادیر مثال را از بریف بگیرید؛ `formal|semi-formal|colloquial` مستقل از `shoma|to|unspecified` است. نام بدون معرفی صریح حدس زده نمی‌شود؛ `--protect` تکرارپذیر را برای نام‌ها/عبارت‌های حساس بدهید. گزینهٔ حفاظت متعلق به پیشنهادگر است و به detector منتقل نشود.

- `detect.py --lang fa --json` قرارداد پیش‌فرض فارسی را حفظ می‌کند؛ فقط گزینه‌های لحن، `tone_review` را اضافه می‌کنند. گزینه‌های لحن با `--lang en` خطا و کد خروج ۲ دارند. کد خروج موفق به معنای کیفیت متن نیست.
- پیشنهادگر بدون `--simplify`، JSON نسخهٔ ۱ را می‌دهد؛ با آن، نسخهٔ ۲ با بخش مستقل `simplification`. `--target-tone` پیشنهادگر فقط همراه `--simplify` معتبر است؛ `--target-address` یا `--format` به آن ندهید. CLI مستقل تازه‌ای برای simplify نسازید.
- ورودی فایل یا `-` برای stdin است؛ `--apply` وجود ندارد. JSON خام و قراردادها را تغییر ندهید؛ برای تغییر قالب گزارش، فقط لایهٔ توضیح انسانی را تنظیم کنید.

### گزارش و تأیید

۱. **یافته‌ها:** هشدار سبکی و لحن/خطاب، با شواهد و نیاز به بررسی بافت؛ هشدار خطاب احتمالی است.
۲. **پیشنهادها:** مکانیکی و زبانی جدا، با `before`، جایگزین، دلیل و offset نسخهٔ دقیق منبع. تأیید انسان برای هر مورد لازم است؛ پیشنهادهای هم‌پوشان یا متعارض با هم پذیرفته نشوند.
۳. **خودداری‌ها:** خودداری ابزار، `insufficient_evidence` و موارد نیازمند بافت را صریح گزارش کنید؛ آن‌ها را «قبول شد» تعبیر نکنید.
۴. **راهنمای انسانی:** تغییرات سنگین یا مبهم فقط برای ویرایش انسانی؛ نفی، شرط، احتمال، نقل‌قول و تغییر مخاطب نیازمند توجه‌اند.
۵. **محدودیت‌ها:** محدودیت واقعی هر خروجی، حفاظت نام با `--protect` و احتمال خطای مثبت/منفی را بیاورید. اگر ابزار دسته‌ای را ندارد، نتیجه‌ای برایش نسازید.

نبود یافته یا پیشنهاد، تأیید کیفیت، طبیعی‌بودن یا صحت ادعا نیست. امتیاز طبیعی‌بودن فارسی نسازید؛ امتیاز انگلیسی را به فارسی تعمیم ندهید. هیچ اصلاحی خودکار انجام نشود؛ پس از ویرایش مورد تأیید انسان دوباره بازبینی کنید و بدون تأیید نهایی متن را آمادهٔ انتشار اعلام نکنید.

## English path (existing behavior and examples)

Two tools live in this folder and they both actually run. Use them. Do not
eyeball this.

```bash
python3 .agents/skills/ig-human/humanize.py draft.txt --report        # clean it, show what changed
python3 .agents/skills/ig-human/detect.py draft.txt                    # score it, five checks
python3 .agents/skills/ig-human/detect.py before.txt after.txt         # prove the delta
```

Both read `slop.json`: 154 stock words and phrases with plain-English
replacements, 18 invisible character classes, 11 typographic substitutions and
16 structural tells. The last block of each list is Instagram-specific, the
vocabulary that only shows up in captions and voiceovers. It is meant to be
edited. If the user has a word they always use that the lexicon strips, take it
out of the file.

## Why this matters more on Instagram than it looks

Captions are short and scripts get said out loud. A written-sounding line in a
600-character caption is a larger share of the text than the same line in an
essay, and a voiceover that nobody could say naturally is obvious in the first
take. The tell here is not a detector flagging the post. The tell is a person
scrolling past something that reads like a brand, or a creator stumbling over
their own script.

## What gets fixed automatically

**1. Invisible characters.** Zero-width spaces and joiners, word joiners, soft
hyphens, byte-order marks, Unicode tag characters, invisible separators,
non-breaking and narrow spaces. A keyboard does not produce these. They survive
copy-paste, they are invisible in every editor, and they are the most
mechanical thing in generated text. `humanize.py` deletes every one, including
any remaining Unicode format character it does not have a name for.

**2. Typography.** Em dash to comma, en dash to hyphen, curly quotes to
straight, ellipsis to three dots, bullet character to hyphen. The em dash pass
is the one that matters: it collapses the dash to a comma and then cleans up
the double punctuation and orphaned periods that leaves behind.

**3. The slop lexicon.** delve, leverage, robust, seamless, crucial, testament
to, "in today's fast-paced world", plus the Instagram block: "stop scrolling",
"in today's video", "follow for more", "tag someone who needs this", "the
algorithm loves", "run don't walk". Each swapped for a plain word or deleted,
with capitalisation preserved and URLs left untouched.

## What does NOT get fixed automatically

Structural tells get **flagged, not rewritten**, because changing the shape of
a sentence needs judgement:

- "It's not just X, it's Y" and "not only X but also Y"
- Rule-of-three triads
- Rhetorical one-word question lines: "The result?"
- The video preamble: "in this video I'm going to show you"
- Emoji bullet lists
- Three or more shouted words in a row
- Hashtag walls
- Reflex bait: "follow for more", "tag someone who", "double tap if"

That list is your job. Rewrite each flagged line by hand, keeping the meaning,
then re-run `detect.py`. This is the part that moves the score from REVIEW to
PASS, and it is the part a script cannot do.

## The five checks

`detect.py` scores five signals 0-100, higher is more human:

| check | what it measures | machine looks like |
| --- | --- | --- |
| BURSTINESS | sentence-length variation | every sentence the same length |
| SPECIFICITY | numbers, names, concrete markers per 100 words | abstract nouns, no figures |
| SLOP DENSITY | lexicon hits per 100 words | stock vocabulary |
| FINGERPRINT | invisible chars, em dashes, curly quotes per 1k chars | typographically perfect |
| VOICE | contractions, person, structural tells | no contractions, staged reveals |

The verdict weights the mean at 60% and the **weakest single check** at 40%,
because one signal is enough. PASS needs an overall of 70+ with no check
below 55.

## Say this honestly

These are five local heuristics modelled on the signals public detectors key
on. They run entirely on the user's machine and nothing is uploaded. They are
**not** GPTZero, Originality, Copyleaks, Winston or Turnitin, they do not call
those APIs, and they cannot promise those verdicts. Fixing what they measure
does tend to move those numbers, because they are measuring the same underlying
things. That is the claim. Do not make a bigger one on the user's behalf, and
do not tell a user their text is undetectable.

## Order of operations

1. `humanize.py draft.txt -o clean.txt --report`
2. Read the structural flags. Rewrite those lines yourself.
3. `detect.py draft.txt clean.txt` to show the before and after.
4. If the verdict is not PASS, fix the weakest check named in the output and go
   again. Two rounds is normal. Five means the draft was written by formula,
   and the fix is a different draft, not more passes.
5. Show the user the cleaned text and the score. Never the score alone.
