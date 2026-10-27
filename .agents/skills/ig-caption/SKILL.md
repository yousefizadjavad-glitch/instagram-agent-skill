---
name: ig-caption
description: >-
  Write the Instagram caption - the line that survives the "... more" cut, the
  body, the single ask, the search terms and the three hashtags - and lint it
  before it goes out. Use when the user says "write the caption", "caption this",
  "what do I put in the description", has a reel or a carousel ready and needs
  the text, or asks about hashtags.
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


# ig-caption

One tool lives in this folder and it runs:

```bash
python3 .agents/skills/ig-caption/caption.py caption.txt
python3 .agents/skills/ig-caption/caption.py caption.txt --keywords "client proposals,agency pricing"
```

It prints the caption the way the feed prints it: the first 125 characters in a
box, everything else behind the tap. Read that box before you read anything
else you wrote.

## First, decide which job this caption has

This is the decision that ruins captions when it is skipped.

**Job A: the video already hooked them.** A Reel carries its own hook in the
first two seconds, spoken and on screen. The caption is not a second hook and
competing with the video is how you lose both. Its job is the ask, the context
that makes the ask make sense, and the words people search.

**Job B: the caption is the content.** A photo, a single image, a carousel
cover that opens a loop. Here line one is the hook and it works exactly like a
Reel hook: concrete, short, and cut off at a cliff rather than mid-clause.

Ask which one you are writing. If the user has a Reel with a strong hook,
write A and say why.

## The shape

```
Line 1      125 characters of visible space. Job A: the ask, plainly.
            Job B: the hook.
            Never a greeting, never a hashtag, never an emoji as the first
            character.
Body        short paragraphs, one line of white space between each. Two to six
            of them. This is where the search terms live.
The ask     one. Comment a keyword, save it, or DM. One.
Hashtags    up to five, on their own line at the bottom, or none.
```

Limit is 2,200 characters and almost nothing needs 2,200. A caption that earns
the tap and then delivers 600 characters beats one that delivers 1,800.

## Hashtags, honestly

Hashtags are not a reach lever any more, and the platform has now said so with
a product change. **Instagram capped hashtags at five per post on 18 December
2025**, down from thirty, telling creators that "using fewer (up to 5) more
targeted hashtags, rather than many generic ones" performs better. Adam Mosseri
had already said in February 2025 that hashtags do not work to increase reach
and are a label, not a distribution lever.

So: up to five, specific, as topic labels. If the user has a block of twenty
saved in their notes app, that block is now dead weight and the linter will
fail it.

`#viral`, `#fyp`, `#explorepage`, `#foryou` describe nothing. Cut them.

## Search terms matter more than hashtags now

Instagram search reads the caption text. So the phrase the user wants to be
found for goes in the caption as a phrase a human would type, in a sentence
that reads normally. "Client proposals" as words in line three, not
"#clientproposals" in a block at the bottom.

Ask for two or three of those terms, then pass them to the linter:

```bash
python3 .agents/skills/ig-caption/caption.py draft.txt --keywords "client proposals,agency pricing"
```

## Rules

- **No link in the caption.** Captions are not clickable. A URL in the body is
  dead text that says "I do not use this platform". Bio or DM.
- **One ask.** Two asks is the same as none. `caption.py` counts them.
- **The keyword ask needs a keyword people can type.** One word, no spaces, no
  emoji, and say it out loud in the video too. `Comment CONTRACT` works.
  `Comment "the contract guide"` does not.
- **Write the first comment separately** if there is a link. Say so in the
  receipt.
- **Emoji as punctuation, not decoration.** The linter flags anything over
  4 per 100 characters.
- **Alt text is worth 20 seconds.** For carousels and photos, write it. It is
  read by screen readers and by Instagram.

## The loop

1. Decide Job A or Job B and say which.
2. Draft it.
3. Run `$ig-human` on it. Captions are short, so slop is louder here than
   anywhere else in the pack.
4. Run `caption.py` with the user's search terms. Fix every FAIL. Decide on
   every WARN out loud rather than silently.
5. Print the copy-ready block, then the receipt:

```
CAPTION READY
job:        A - the reel carries the hook
visible:    118 of 125 characters used before the cut
ask:        one, comment CONTRACT
hashtags:   3
search:     "client proposals" in line 3, "agency pricing" in line 5
linter:     READY
```

Nothing is posted. The user pastes it.
