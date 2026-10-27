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
preceding specific questions require human review; exceptions are explanatory,
not an automatic semantic filter.

Coverage is intentionally limited: no broad paraphrase detection, semantic
repetition, full morphology/diacritic normalization, dialect coverage or reliable
reported-speech attribution. Markdown/code quotation conventions and malformed
quote punctuation are not fully parsed. An empty review only means no initial
rule matched. No Persian auto-rewriting was added to `humanize.py` and no
calibration data or numerical Persian quality model is claimed.
