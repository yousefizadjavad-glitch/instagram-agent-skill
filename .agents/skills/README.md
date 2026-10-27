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
proof of human authorship or a prediction of viral performance. The humanizer
removes U+200C, so do not use it on Persian without adapting the rules.

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
