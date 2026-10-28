# Instagram skills for Codex

This directory contains the Codex copies of all 13 skills in `skills/`.
The original skills, README, template, and Claude plugin configuration are
unchanged. Python tools and JSON resources stay beside their skill files.

## Use

Open a new Codex task with this repository so project skills can be discovered
from `.agents/skills/`. Request `$ig-reel`, for example. Discovery depends on
the client and task; adding files does not reload the current task's catalog.
If a skill is unavailable in the catalog, explicitly ask Codex to read
`.agents/skills/ig-reel/SKILL.md` and follow it. Cross-skill references use this
same fallback: `ig-reel` reads `ig-human` and runs its bundled tools.

Run shell examples from the repository root. Python 3 is the only dependency
for the six local tools; no pip install, Claude installation, API key, or
Instagram credentials are needed. Example:

```bash
python3 -B .agents/skills/ig-reel/hookscore.py --hook "Stop spending 5 hours on every freelance proposal."
```

The standard-library tools also accept stdin (`-`) and `--json`. The caption
linter returns exit 1 for REVIEW/FAIL. The detector's text mode returns exit 1
for non-PASS; JSON mode returns 0, so inspect its `verdict`. A low score is not
necessarily an execution error. These are English-oriented heuristics, not
proof of human authorship or a prediction of viral performance. The humanizer preserves context-valid Persian U+200C but has no Persian
rewriting policy; do not use it for automatic Persian rewriting.

## Personal context and outputs

The Cloud convention is `/workspace/instagram-agent-data/`, outside the
checkout. Use it consistently for `voice.md`, `swipe.md`, `log.md`, and
`plan.md`, or specify another location in the task. The original
`templates/voice.md` is available as a template; do not invent a user's voice
or overwrite an existing profile. Context files are not shared automatically
between Cloud tasks. Keep required context in storage you control and make it
available to each task. No credentials belong in these files.

No data directory is created by this adaptation. For a test without file
writes, provide the voice in chat and send text through stdin; set
`PYTHONDONTWRITEBYTECODE=1` to avoid Python cache files.

## Optional capabilities

- `ig-viral`: analyze supplied TSV data locally. Live research requires
  available browsing/network access; optional YouTube research uses `yt-dlp`.
- `ig-carousel`: drafting and HTML need no additional package; image/PDF
  rendering needs a suitable browser or rendering tool.
- `ig-repurpose`: supplied transcripts work directly; fetching transcripts or
  editing footage requires separate tools.

None of these skills publishes posts or sends messages. The user handles
publication. Keep the Codex copies in sync deliberately when upstream skills
change; they are independent copies, not generated on startup.

## Unicode text core (Codex only)

`text_core.py` supplies shared Unicode tokenization, numeric normalization and
sentence boundaries to the humanizer, detector and Reel tools. Keep this file
with the skill pack; scripts resolve it relative to their own location.

- Context-valid U+200C between Arabic-script letters (including intervening
  combining marks) is preserved and is not a fingerprint penalty. Leading,
  trailing, repeated, Latin-adjacent or digit-adjacent ZWNJ is not exempt.
  This is a script-context check, not Persian language or spelling detection.
  Other format controls retain the existing cleanup and penalty policy.
- Persian, Arabic-Indic and ASCII decimal digits are normalized for analysis;
  Arabic thousands/decimal separators and percent signs have ASCII equivalents.
  Displayed source text is preserved. A ZWNJ compound counts as one word.
- To preserve English scoring, the detector still counts letter words and
  excludes numeric-only tokens; Reel tools count numbers and currency tokens.
  Existing ASCII decimal-token behavior is retained rather than redefining it.
- Persian `؟` is a sentence boundary. Newlines remain boundaries for the
  humanizer and detector; Reel timing keeps one input line per edit beat.
- English scoring vocabularies, thresholds and the default 165 wpm are unchanged.
  Persian/mixed-language scores are **not validated naturalness or hook-quality
  measurements**. Timing is a word-count estimate, not a calibrated Persian
  speech rate; use an actual reading and `--wpm` to plan a recording.

Run the standard-library tests, including English regression checks against the
unchanged original scripts, without dependencies:

```bash
python3 -B -m unittest discover -s .agents/skills/tests -v
```

## Persian style review (phase two, part one)

The Codex detector has an explicit `--lang fa` path, independent of English
scoring. Omitted `--lang` and `--lang en` keep the existing English CLI, JSON
schema, scoring and exit-code behavior. No language auto-detection is used.

```bash
python3 -B .agents/skills/ig-human/detect.py draft.txt --lang fa
python3 -B .agents/skills/ig-human/detect.py draft.txt --lang fa --json
python3 -B .agents/skills/ig-human/detect.py before.txt after.txt --lang fa --json
```

Persian mode returns an editorial review, never a naturalness score, authorship
verdict or numerical comparison. Both text and JSON modes exit 0 for a completed
review, including when findings exist. Invalid CLI options retain argparse exit
2; file/JSON failures remain execution errors. Two files produce separate reviews
(a JSON array), with no quality delta. Stdin `-` and execution outside the checkout
are supported.

`persian_review.py` uses the existing `text_core.words` for counts. It retains the
exact source in `text`; each finding includes `evidence`, `start`, `end`, `reason`,
`suggestion`, exceptions, relevant tones and contextual attribution status.
Offsets are zero-based Python Unicode code-point indexes, end exclusive, into
the original text (not UTF-8 bytes or UTF-16 units). The analysis-only mapping of
Arabic yeh/kaf to Persian variants keeps character positions intact. ZWNJ,
combining marks, punctuation, digits and mixed English content remain unchanged.

`fa_style_rules.json` is a small manually authored editorial lexicon, not a
validated corpus. Each rule has a stable ID, regex pattern, warning type, reason,
exceptions, relevant tones and suggestion. The six categories are cliché
introductions, vague promotion, absolute promises, generic engagement requests,
heavy administrative phrasing and obvious consecutive word repetition. English
stock vocabulary is not evaluated in Persian mode. `--lexicon` may select a
custom language-specific JSON file: Persian requires a `rules` array with the
same fields; English retains the existing `slop.json` schema.

Quoted findings are retained for review and marked `quoted: true` and
`attribution: requires_quote_review`; they are not attributed to the author.
Guillemets, curly and ASCII quotes, nested and unclosed spans are handled
conservatively. Apostrophes inside words are not treated as quote delimiters.
Unquoted findings use `requires_context_review`, not a confirmed defect.
Negation, legal guarantees, deliberate emphasis, formal correspondence and
preceding specific questions generally require human review. Three narrow contextual
exceptions now suppress clear matches (see the Persian section below); explanatory
exceptions in the lexicon are not a general semantic filter.

Coverage is intentionally limited: no broad paraphrase detection, semantic
repetition, full morphology/diacritic normalization, dialect coverage or reliable
reported-speech attribution. Markdown/code quotation conventions and malformed
quote punctuation are not fully parsed. An empty review only means no initial
rule matched. No Persian auto-rewriting was added to `humanize.py` and no
calibration data or numerical Persian quality model is claimed.

## بررسی اختیاری سازگاری لحن فارسی

این قابلیت فقط با گزینه‌های جدید فعال می‌شود. اجرای قبلی `--lang fa`، خروجی
JSON و متن آن، قواعد `fa_style_rules.json` و مسیر انگلیسی بدون تغییر باقی می‌مانند.
هیچ نمرهٔ طبیعی‌بودن یا بازنویسی خودکاری اضافه نشده است.

```bash
python3 -B .agents/skills/ig-human/detect.py draft.txt --lang fa --tone-check --json
python3 -B .agents/skills/ig-human/detect.py draft.txt --lang fa --target-tone semi-formal --target-address shoma
```

- `--tone-check` ناسازگاری داخلی را بدون حدس لحن غالب بررسی می‌کند.
- `--target-tone formal|semi-formal|colloquial` سیاست لحن هدف را مشخص می‌کند.
  در رسمی، عبارت‌های آشکار محاوره‌ای؛ در نیمه‌رسمی و محاوره‌ای، عبارت‌های
  سنگین اداری برای بررسی پیشنهاد می‌شوند. این سیاست محدود، تعریف جامع لحن نیست.
- `--target-address shoma|to|unspecified` مستقل از لحن است؛ «شما» در متن
  محاوره‌ای مجاز است. پیش‌فرض `unspecified` است.
- تعیین هر هدف، حتی `--target-address unspecified`، بررسی جدید را فعال می‌کند.
  این گزینه‌ها بدون `--lang fa` با خطای آرگومان و کد خروج ۲ رد می‌شوند.

منطق جدید در `ig-human/persian_tone.py` قرار دارد. تطبیق‌ها محدود به عبارت‌های
صریح و دارای مرز واژه‌اند؛ «شما می‌توانید» و «تو می‌تونی» شاهد خطاب‌اند، اما
«تو خونه» یا پسوند فعل به‌تنهایی شاهد کافی نیستند. واژه‌های عمومی مانند سلام،
لطفاً و ثبت، ناسازگاری اداری/محاوره‌ای ایجاد نمی‌کنند. برای مثال
«شما انتخاب کنید؛ تو می‌تونی» دو شاهد مستقل برای تغییر احتمالی خطاب دارد؛
«مقتضی است فرم رو پر کنی؛ یادت نره» ترکیب دو سبک را نشان می‌دهد.

مقایسهٔ خطاب در دو شاهد صریح و نزدیک، داخل بند یا دو بند متوالی انجام می‌شود.
یک سطر خالی به‌تنهایی تغییر مخاطب را اثبات نمی‌کند. عنوان مخاطب شناخته‌شده،
نشانگر صریح تغییر مخاطب، نقل‌قول و گفتار مستثنا زنجیرهٔ خطاب را قطع می‌کنند.
مقایسهٔ سبک اداری/محاوره‌ای همچنان در محدودهٔ یک بند باقی می‌ماند.
نقل‌قول‌های گیومه، خمیده و ASCII، تو‌در‌تو و باز، از استخراج شواهد لحن کنار
گذاشته می‌شوند. دیالوگ فقط با برچسب‌های محدود مانند «مشتری:» و «پشتیبان:»
شناخته می‌شود؛ خط تیره به‌تنهایی دیالوگ نیست. پس از «گفت»، «نوشت»، «پرسید» و
«گفتند»، باقی جمله تا پایان جمله یا سطر محافظه‌کارانه کنار گذاشته می‌شود.
مثلاً «او گفت: «تو می‌تونی». شما فرم را تکمیل کنید.» هشدار تغییر خطاب ندارد.
این استثناها فقط برای قابلیت جدیدند؛ بازبینی واژگانی قبلی همچنان مستقل است.

در JSON فقط هنگام فعال‌سازی، `tone_review` به گزارش اضافه می‌شود:

- `target_tone` و `target_address`: تنظیم‌های صریح، بدون استنباط هدف.
- `assessment`: مقدار `findings_present`، `no_findings` یا `insufficient_evidence`.
  دو شاهد خطاب یا شاهد مرتبط با هدف صریح می‌تواند برای ارزیابی کافی باشد؛
  شاهد مبهم یا منفرد بدون هدف معمولاً به شواهد ناکافی منجر می‌شود.
- `findings`: شناسهٔ قاعده، دلیل، پیشنهاد، `requires_context_review` و آرایهٔ
  `evidence`. هر شاهد شامل متن مستقل، `kind` و `start/end` است؛ شاهد خطاب
  همچنین `value` دارد. offsetها اندیس Unicode پایتون در ورودی دست‌نخورده‌اند
  و انتهای بازه غیرشامل است؛ نه اندیس بایت UTF-8 یا واحد UTF-16.
- `excluded_spans`: بازه‌ها و دلیل استثنا؛ بازه‌های تو‌در‌تو ممکن است هم‌پوشان باشند.
- `limitations`: محدودیت‌های پوشش و نیاز به قضاوت انسانی.

شناسه‌های فعلی: `fa-address-shift`، `fa-target-address`، `fa-mixed-register`
و `fa-target-tone`. یک عبارت ممکن است هم شاهد اختلاط داخلی و هم ناسازگاری با
هدف باشد؛ این‌ها دو دلیل مستقل دارند. متن خروجی شواهد را زیر هر دلیل نشان می‌دهد.

متن کوتاه صرفاً به‌خاطر کوتاهی کنار گذاشته نمی‌شود؛ دو شاهد صریح می‌توانند
هشدار بسازند. نبود یافته تأیید یکدستی نیست. تغییر مخاطب ضمنی، کنایه، طنز، گویش‌ها،
صرف کامل و عمدی‌بودن تغییر پشتیبانی جامع ندارند؛ استثنای محافظه‌کارانهٔ گفتار
ممکن است برخی شواهد واقعی را نیز کنار بگذارد. این قواعد با پیکرهٔ انسانی
کالیبره نشده‌اند و هیچ عدد دقت یا امتیاز کیفیت ادعا نمی‌شود.

stdin، JSON، اجرای خارج از پوشه و مقایسهٔ دو فایل پشتیبانی می‌شوند؛ دو فایل
گزارش مستقل دارند و اختلاف نمره تولید نمی‌شود. بازبینی موفق فارسی، حتی با
یافته، کد خروج ۰ دارد. اجرای تست‌های قبلی، ۲۳ نمونهٔ طراحی و قراردادهای جدید:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s .agents/skills/tests -v
```

## پیشنهاد مستقل اصلاح محدود فارسی — مرحلهٔ اول

این ابزار آفلاین تنها پیشنهاد و گزارش تولید می‌کند و فایل ورودی را تغییر نمی‌دهد.
مسیرهای `humanize.py` و `detect.py` و بازبینی‌های قبلی تغییری نکرده‌اند.
هیچ API، مدل زبانی، امتیاز طبیعی‌بودن، تبدیل لحن، پروفایل قالب، بازنویسی ساختاری
یا گزینهٔ `--apply` در این مرحله وجود ندارد.

```bash
python3 -B .agents/skills/ig-human/persian_rewrite.py draft.txt --json
python3 -B .agents/skills/ig-human/persian_rewrite.py - --protect "برند  نو" --json
```

ورودی فایل و stdin باید UTF-8 باشد. ابزار متن اصلی، CRLF، فاصله‌ها و نیم‌فاصله‌ها
را در `source_text` حفظ می‌کند. `source_sha256` هش SHA256 متن UTF-8 اصلی است.
خروجی پیش‌فرض گزارش متنی است؛ `--json` قرارداد نسخهٔ ۱ زیر را ارائه می‌کند:

- `schema_version`، `language`، `mode` و `engine`: نسخه و نوع گزارش آفلاین.
- `source_text` و `source_sha256`: متن اصلی و شناسهٔ محتوای آن.
- `options.protect`: عبارت‌های دقیق و تکرارپذیر `--protect`؛ عبارت خالی مجاز نیست.
- `protected_spans`: بازه‌های دارای `start`، `end`، `text` و `reason`؛ بازه‌های
  هم‌پوشان برای حفظ دلایل مستقل باقی می‌مانند و هر هم‌پوشانی مانع پیشنهاد است.
- `suggestions`: شناسه، قاعده، `before`، `replacement`، بازه، دلیل،
  `requires_confirmation: true`، بررسی‌های محدود و `conflicts_with`.
- `abstentions`: نامزدهای کنارگذاشته‌شده با بازه، متن قبل، قاعده و دلیل خودداری.
  این آرایه فهرست تمام مشکلات احتمالی متن نیست.
- `limitations`: محدودیت‌های پوشش و نیاز به بازبینی انسانی.
- `status`: مقدار `suggestions_available`، `insufficient_context` برای نامزدهای
  مسدود بدون پیشنهاد، یا `no_suggestions`؛ نبود پیشنهاد، تأیید کیفیت متن نیست.

تمام offsetها صفرمبنا، با انتهای غیرشامل و برحسب Unicode پایتون در متن اصلی‌اند؛
برای هر پیشنهاد و خودداری، `source_text[start:end] == before` برقرار است.
پیشنهادها مستقل‌اند و زنجیره‌ای اعمال نمی‌شوند. `conflicts_with` گزینه‌های
هم‌پوشان را معرفی می‌کند؛ `validate_selection` انتخاب مشترک بازه‌های هم‌پوشان،
شناسهٔ ناشناخته و انتخاب تکراری را رد می‌کند. این تابع چیزی را اعمال نمی‌کند.

قواعد فقط دو دسته‌اند: تبدیل فاصله‌های ASCII اضافی میان حروف فارسی به یک فاصله،
و تبدیل یک فاصله در فهرست محدود ترکیب‌هایی مانند «می توانم» به «می‌توانم».
این فهرست در `persian_rewrite_rules.json` است؛ پسوندها به‌طور عمومی تحلیل
نمی‌شوند و نیم‌فاصلهٔ موجود، newline و متن انگلیسی پاک‌سازی نمی‌شوند.
مثلاً «سلام  دوستان» پیشنهاد حذف یک فاصله می‌گیرد؛ متن صحیح می‌تواند هیچ
پیشنهادی نداشته باشد.

حفاظت پیش‌فرض شامل URL، ایمیل، هشتگ، منشن، اعداد Unicode، قیمت با واحدهای
شناخته‌شده، درصد، تاریخ و ساعت عددی، قطعه‌های لاتین و کدهای لاتین محصول است.
نام یا کد فارسی ناشناخته را با `--protect` قفل کنید. حفاظت تشخیص جامع اطلاعات
شخصی، تاریخ نوشتاری یا موجودیت نامدار نیست. همهٔ وقوع‌های عبارت انتخابی قفل
می‌شوند. عدد و لینک مانند «۱٬۲۵۰٬۰۰۰ تومان» و
`https://example.com/p?id=۱۲&x=a` عیناً باقی می‌مانند.

نقل‌قول بسته، تو‌در‌تو و باز تا پایان، دیالوگ با برچسب‌های محدود مانند «مشتری:»،
گفتار دارای نشانگرهایی مانند «گفت»، کد و چیدمان مبهم کنار گذاشته می‌شوند.
سطر دارای تورفتگی، tab، جداکنندهٔ جدول، نشان فهرست یا کنترل جهت مشکوک محافظت
می‌شود. تشخیص شعر، نام، دیالوگ و چیدمان بی‌علامت کامل نیست؛ حتی پیشنهاد فاصله
نیازمند تأیید است.

برای کاهش ریسک، بخش‌هایی با نشانه‌های محدود نفی، شرط، قطعیت، کمیت و خطاب
(مانند «نیست»، «اگر»، «شاید»، «تضمینی»، «شما» و «تو») به‌صورت محافظه‌کارانه
قفل می‌شوند. این روش می‌تواند پیشنهاد مفید را هم کنار بگذارد و تضمین حفظ معنا
نیست. اعتبارسنج جداگانه فقط تغییر مکانیکی مجاز، تطبیق متن اصلی و عدم برخورد
با حفاظت را بررسی می‌کند؛ هیچ تأیید معنایی تولید نمی‌شود.

بازبینی موفق با کد ۰، خطای آرگومان با کد ۲ و خطای فایل یا UTF-8 با کد ۱ پایان
می‌یابد. اجرا از بیرون پوشهٔ پروژه هم پشتیبانی می‌شود. تست‌های حفاظت، offset،
نیم‌فاصله، ورودی فایل و stdin، عدم تغییر فایل و قراردادهای قبلی:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s .agents/skills/tests
```

## ساده‌سازی اختیاری فارسی — بخش اول

```bash
python3 -B .agents/skills/ig-human/persian_rewrite.py draft.txt --simplify --json
python3 -B .agents/skills/ig-human/persian_rewrite.py - --simplify --target-tone semi-formal --json
```

بدون `--simplify` قرارداد و JSON نسخهٔ ۱ دقیقاً حفظ می‌شود. با این گزینه،
`schema_version` برابر ۲ و بخش مستقل `simplification` اضافه می‌شود. فهرست
`suggestions` اصلی همچنان فقط مکانیکی است. `--target-tone` فقط همراه
`--simplify` معتبر است و مقادیر `formal`، `semi-formal` و `colloquial` را
می‌پذیرد؛ بدون انتخاب، صورت ساده و محترمانه پیشنهاد می‌شود و لحن حدس زده نمی‌شود.
مسیرهای انگلیسی، detector، humanizer و بررسی لحن قبلی تغییر نکرده‌اند.

ماژول `persian_simplify.py` از قواعد مستقل `persian_simplify_rules.json` و
اعتبارسنج مستقل `persian_simplify_checks.py` استفاده می‌کند؛ اعتبارسنج مکانیکی
و حفاظت نسخهٔ ۱ دست‌نخورده‌اند. چهار خانوادهٔ محدود عبارت پشتیبانی می‌شوند:

- «در خصوص» به «دربارهٔ»، تنها پیش از موضوع‌های فهرست‌شده مانند ارسال یا مدل.
- «به منظور» به «برای»، تنها پیش از عمل‌هایی مانند بررسی و ارسال.
- «از طریق ایمیل» به «با ایمیل»، تنها پیش از افعال محدود ارسال/دریافت.
- درخواست کامل «خواهشمند است تصویر رسید/فایل/رسید/شمارهٔ سفارش را ارسال فرمایید»
  به «لطفاً … را ارسال کنید». برای محاوره‌ای «لطفاً … را بفرستید» پیشنهاد
  می‌شود؛ خطاب جمع حفظ می‌شود. درخواست ناقص یا دارای ادامهٔ عملی دیگر رد می‌شود.

این‌ها قواعد عمومی واژه‌جایگزینی نیستند. «جهت شمال»، «در راستای دیوار» و
«از طریق تونل» تبدیل نمی‌شوند. اصلاح سبک، کوتاه‌کردن اجباری متن یا شکستن جمله
انجام نمی‌شود؛ جملهٔ طبیعی می‌تواند بدون پیشنهاد بماند.

در `simplification` فیلدهای `target_tone`، `suggestions`، `guidance`،
`abstentions`، `limitations` و `status` وجود دارند. هر پیشنهاد شامل شناسهٔ
`l...`، `rule_id`، `start/end`، `before`، `replacement`، `reason` و
`requires_confirmation: true` است. offsetها روی متن اصلی، صفرمبنا و انتها
غیرشامل‌اند. `semantic_review: required` به معنی نیاز به بازبینی انسان است؛
عبور از کنترل محدود، تأیید حفظ معنا نیست.

`guidance` برای ساختار سنگین یا حساس صرفاً راهنمای انسانی با `replacement: null`
دارد؛ `abstentions` دلیل خودداری از نامزد را ثبت می‌کند. وضعیت‌ها:
`suggestions_available`، `guidance_only`، `insufficient_context` و
`no_suggestions`. نبود پیشنهاد تأیید کیفیت نیست. شمار واژهٔ بیش از ۳۵ فقط یک
آستانهٔ اولیهٔ راهنمای انسانی برای جملهٔ فارسی است؛ معیار طبیعی‌بودن نیست.

پیشنهادهای تکراری با بازه و جایگزین یکسان حذف می‌شوند؛ موارد هم‌پوشان به‌عنوان
تعارض باقی می‌مانند. در نسخهٔ ۲، `conflicts_with` بین فهرست مکانیکی و زبانی نیز
محاسبه می‌شود؛ برای بررسی انتخاب مشترک باید هر دو فهرست به `validate_selection`
داده شوند. هیچ انتخاب یا اعمال خودکاری صورت نمی‌گیرد و `--apply` وجود ندارد.

حفاظت URL، عدد، قیمت، تاریخ، برند صریح با `--protect`، نقل‌قول، دیالوگ و چیدمان
مانند نسخهٔ ۱ برقرار است. مسیر جدید موانع جداگانه‌ای برای نفی، شرط، احتمال،
خطاب، حقوق و نشانه‌های محدود کنایه دارد. در جملهٔ حساس جایگزین تولید نمی‌شود؛
ممکن است راهنما یا دلیل خودداری ارائه شود. نقل‌قول و دیالوگ به نویسنده نسبت
داده نمی‌شوند. برند و کنایهٔ ناشناخته، نفی پیچیده و بافت حقوقی پوشش جامع ندارند؛
همهٔ پیشنهادها نیازمند تأییدند و حفظ معنا یا طبیعی‌ترشدن تضمین نمی‌شود.

نمونه: «در خصوص ارسال سفارش سؤال دارم.» پیشنهاد «دربارهٔ» می‌گیرد؛
«به منظور بررسی محصول، بسته را باز می‌کنم.» پیشنهاد «برای» می‌گیرد؛
«اگر به منظور بررسی محصول بسته را باز کنید، نتیجه مشخص می‌شود.» به‌علت شرط
جایگزین نمی‌گیرد. فایل ورودی، CRLF و متن اصلی تغییر نمی‌کنند؛ کدهای خروج
موفقیت ۰، آرگومان نامعتبر ۲ و خطای ورودی ۱ باقی می‌مانند.


## اصلاحات اولویت اول ارزیابی مصنوعی فارسی

این اصلاحات فقط سه مسئلهٔ نفی، پیوستگی خطاب و حفاظت نام را پوشش می‌دهند؛
قالب CLI و نسخه‌های JSON ۱ و ۲ و مسیر انگلیسی تغییری نکرده‌اند. یافته‌های
نمونه‌های مسئله‌دار عمداً تغییر کرده‌اند؛ اعمال خودکار همچنان وجود ندارد.

- در اعتبارسنج مستقل ساده‌سازی، خانواده‌های محدود «ندارم/نداریم»، «نیستم»،
  «نبودم»، «نشدند/نشوند»، «نخواهم»، «نکنید»، «نداشته‌ام»، «نتوانستم» و چند
  صورت «نمی‌دانم/نمی دانیم/نمیدانم» و نشانگرهای «هرگز/هیچ» بررسی می‌شوند.
  نامزدهای مربوط با `negation_requires_review` کنار گذاشته می‌شوند؛ حفاظت‌های
  قبلی ممکن است زودتر دلیل `protected_span` بدهند. برای مثال «در خصوص ارسال
  سفارش اطلاع ندارم» دیگر پیشنهاد «دربارهٔ» نمی‌گیرد. مرز واژه مانع تطبیق
  صورت‌هایی مانند «نامدار» یا «نیستان» با این خانوادهٔ جدید است. این قواعد
  صرف‌شناسی یا تحلیل جامع دامنهٔ نفی نیستند؛ ابهام و جمله‌بندی همچنان نیازمند
  بررسی انسان‌اند. قواعد مکانیکی نفی در نسخهٔ ۱ گسترش نیافته‌اند.
- «شما سفارش را ثبت کنید؛ تو هزینه را پرداخت کن» و «شما بخوانید.\n\nتو می‌تونی
  نظر بدی» دو شاهد خطاب دارند و `fa-address-shift` می‌گیرند، با وضعیت
  `requires_context_review`؛ بی‌دلیل‌بودن تغییر اثبات نمی‌شود. فقط چند ساختار
  صریح اضافه شده‌اند؛ از پسوند عمومی فعل یا «تو خونه» مخاطب حدس زده نمی‌شود.
  فاصلهٔ بیش از ۲۰۰ نویسه میان شواهد، چند جملهٔ واسط، سه شکست سطر متوالی و
  جداکنندهٔ بخش مانع مقایسه‌اند. «خطاب به»، «مخاطب بعدی»، «تغییر مخاطب» و
  عنوان‌هایی مانند «دانش‌آموز عزیز» مرز مخاطب‌اند. نقل‌قول و دیالوگ برچسب‌دار
  همچنان مستثنا هستند؛ این محدودیت‌ها ممکن است تغییر خطاب واقعی را هم از دست بدهند.
- `--protect` همچنان راه اصلی معرفی دقیق نام است و همهٔ وقوع‌های عبارت را
  عیناً قفل می‌کند. ابزار تشخیص عمومی نام برند ندارد. بدون معرفی نام، تنها
  پس از نشانگر صریح «برند»، «نام تجاری» یا «نام محصول»، محدوده تا نشانهٔ پایان
  جمله، نقطه‌ویرگول یا newline با دلیل `suspected_name_context` محافظت می‌شود.
  این یک محدودهٔ مشکوک است، نه نام شناسایی‌شده؛ ممکن است بیش‌ازحد محافظت شود.
  در این حالت، خروجی یادآور می‌شود که نام دقیق با `--protect` مشخص شود.
  نام بی‌نشانگری مانند «سپیدار  نو» خودکار شناخته نمی‌شود و فاصله‌اش می‌تواند
  پیشنهاد اصلاح بگیرد؛ برای حفظ قطعی نگارش ورودی از `--protect "سپیدار  نو"`
  استفاده کنید. حتی با معرفی نام، هیچ تضمین جامع حفظ معنا مطرح نیست.

در C10 مصنوعی، هم با `--protect "برند  نو"` و هم با خودداری پس از نشانگر
«برند»، فاصلهٔ نام دست‌نخورده می‌ماند؛ فقط فاصلهٔ اضافی «سلام  دوستان» پیشنهاد
اصلاح می‌گیرد. هیچ متن پیشنهادی روی فایل اعمال نمی‌شود.


## اصلاحات اولویت دوم بازبینی فارسی

`persian_review_context.py` فقط سه استثنای محدود را برای قواعد اصلی بازبینی
پیاده می‌کند. API، گزینه‌های CLI، کلیدهای JSON و قرارداد offset تغییر نکرده‌اند؛
فهرست یافته‌ها برای این استثناهای روشن عمداً تغییر می‌کند. هیچ متن یا فایلی
بازنویسی نمی‌شود. قواعد سفارشی با شناسه‌های مستقل وارد این استثناها نمی‌شوند.

- **نفی روشن ادعا:** تطبیق «موفقیت/نتیجه … تضمینی» که بلافاصله با فاصلهٔ معمولی
  و «نیست»، «نیستند»، «نبود» یا «نبوده است» پایان بند بیاید، از هشدار وعدهٔ
  مطلق کنار گذاشته می‌شود. «این موفقیت تضمینی نیست؛ نتیجه به تمرین بستگی دارد»
  دیگر آن هشدار را نمی‌گیرد. پرسش، شرط، احتمال، نفی بیرونی و ادامهٔ توضیحی
  مبهم مانند «اینکه موفقیت تضمینی نیست درست نیست» همچنان نیازمند بررسی بافت‌اند.
  نفی از بیرون نقل‌قول به ادعای داخل نقل‌قول نسبت داده نمی‌شود؛ نقل‌قول مثبت
  همچنان یافته با `quoted: true` و `requires_quote_review` دارد. نفی روشن درون
  همان نقل‌قول می‌تواند مستثنا شود. این تحلیل کامل نفی یا دامنهٔ آن نیست.
- **CTA مرتبط:** درخواست نظر مانند «نظرتان را بنویسید» فقط وقتی از هشدار عمومی
  کنار گذاشته می‌شود که بلافاصله پس از پرسش کامل و محدودِ ترجیح/انتخاب یا مقایسه
  بیاید؛ برای مثال «کدام رنگ را ترجیح می‌دهید؟» یا «کدام رنگ برای میز کوچک
  مناسب‌تر است؟». موضوع‌ها و فعل‌ها فهرست محدود دارند. صرف علامت سؤال، پرسش
  بله/خیر، سؤال انگلیسی، جملهٔ واسط، دو شکست سطر، مرز نقل‌قول یا درخواست لایک
  کافی نیست. درخواست نظر با ادامهٔ موضوعی تازه نیز مستثنا نمی‌شود. حداکثر یک
  شکست سطر معمولی مجاز است. موارد ناشناخته همچنان برای بررسی بافت باقی می‌مانند؛
  این ابزار ارتباط معنایی همهٔ پرسش‌ها را تشخیص نمی‌دهد.
- **تأکید عاطفی:** دقیقاً دو «خیلی» پیش از صورت‌های محدود اول‌شخص مثل «خوشحالم»،
  «خوشحالیم»، «دلتنگم»، «ممنونم» و «متشکرم» در پایان بند، بدون نشانهٔ ابهام یا
  نفی نزدیک، از هشدار تکرار کنار گذاشته می‌شوند. «خیلی خیلی خوشحالم!» الزاماً
  خطا نیست. سه تکرار، حلقهٔ اسمی مانند «خانه‌ها خانه‌ها»، پرسش و جمله‌های مبهم
  همچنان بازبینی می‌شوند. این تشخیص جامع تأکید، کنایه، احساس یا طبیعی‌بودن نیست.

برای C5، C6 و R7 مصنوعیِ ارزیابی قبلی، خروجی `findings` اکنون خالی است؛ این
به معنی تأیید کیفیت کلی متن نیست. یافتهٔ مستقل دیگری در همان متن حذف نمی‌شود.
تمام موارد نامطمئن همچنان `requires_context_review` یا `requires_quote_review`
دارند و پیشنهادشان دستور اعمال خودکار نیست. قرارداد انگلیسی و humanizer تغییر
نکرده است. تست‌ها شامل مثال‌های مثبت و نقض، نقل‌قول، نفی مبهم، متن ترکیبی،
offset، فایل و stdin و خروجی JSON هستند؛ این نمونه‌های مصنوعی سنجش دقت عمومی نیستند.
