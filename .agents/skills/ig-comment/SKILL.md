---
name: ig-comment
description: >-
  Write comments on other people's Instagram posts and reels that read as a
  person with an opinion, not a bot. Use when the user pastes a post or a reel
  and wants a comment, says "comment on this", "engage with this", "what do I
  say here", or wants a batch for their daily engagement round.
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


# ig-comment

Commenting is the highest-leverage twenty minutes on Instagram and the easiest
to do badly. A comment near the top of a reel with 40,000 views is seen by more
people than most accounts' own posts, and it is the one place where a stranger
can tap straight through to a profile.

A generic comment is worse than none. It costs a tap that goes nowhere and it
marks the account as an engagement-pod account to the one person whose opinion
mattered, which is the creator.

## Input

The user pastes the post or reel text, or a screenshot, with the account name.
If they give a URL you cannot open, ask them to paste it. Do not use a browser
tool to scrape the feed and do not post anything.

## The nine comment types

Pick by what the post actually is. Never default to type 1.

| # | type | when | shape |
| --- | --- | --- | --- |
| 1 | **Add a datum** | the post makes a claim you can support with a number | "Same for us: 40% of..." |
| 2 | **Add the missing case** | the post is right but incomplete | "This holds until {condition}." |
| 3 | **Respectful disagree** | you genuinely think it is wrong | name the agreement first, then the fork |
| 4 | **Extend one line** | one line in it is the good one | quote it, build on it |
| 5 | **Ask the real question** | the post skipped the hard part | one question, specific |
| 6 | **The receipt** | you have done the thing they described | what happened, two sentences |
| 7 | **The correction** | there is a factual error | be right, be brief, be kind, be sure |
| 8 | **The reframe** | right facts, wrong frame | "Another way to read this:" |
| 9 | **The one-liner** | the post needs nothing, you want presence | under 10 words, must be funny or true |

## Rules

- **One to three sentences.** Instagram comments are read in a narrow column
  under a video. A paragraph gets collapsed behind "more" and nobody taps it.
- **Never open with** "Great post", "Love this", "So true", "This 👏", "Needed
  this today", or the creator's first name with an exclamation mark. All of
  them are invisible.
- **No emoji-only comments** and no emoji as the first character.
- **Never restate the reel.** Everybody watching just watched it.
- **One idea.** A comment with two points reads as a hijack.
- **Say the specific thing.** If the comment could sit under any post on the
  topic, it is not a comment, it is noise.
- **No pitching, ever.** Not the offer, not the link, not "check out my page".
  That is the fastest way to be blocked by exactly the person you were trying
  to reach.
- **Early matters more here than anywhere.** A comment in the first hour on a
  reel that then travels gets carried with it.

## Output

Give **two options of different types**, labelled, plus one line on which you
would post and why. Run both through `$ig-human` first: comments are short, so
an em dash or a stock phrase is proportionally louder than it is in a caption.

```
COMMENT OPTIONS  (on @acct's reel about pricing)

[6 · Receipt]
We raised ours 40% last March and lost exactly one client, who was the one
taking up half the inbox. Took eight months to stop being scared of it.

[3 · Respectful disagree]
Agree on the anchoring. The part I would push back on is doing it mid-project.
We tried that and it cost us a renewal that was otherwise fine.

Post the first. It concedes something and it has a number in it.
```

## Batch mode

For an engagement round, ask for the 5 to 10 posts as pasted text in one
message, return one comment each in a single block, and keep a running note in
`/workspace/instagram-agent-data/log.md` of who has been commented on this week.
Commenting on the same three accounts every day is visible and it looks like
exactly what it is.

## Never

Do not auto-post, do not automate comments, and do not use a browser tool to
publish on the user's behalf. Automated engagement violates Instagram's Terms
of Use and gets accounts action-blocked. This skill writes the comment. The
user posts it.
