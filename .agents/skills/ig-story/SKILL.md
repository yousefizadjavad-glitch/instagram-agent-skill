---
name: ig-story
description: >-
  Write the day's Instagram Stories - the frame-by-frame sequence, which
  stickers to use where, and the one that moves people into the DMs. Use when
  the user says "stories", "what do I post on my story", "story sequence",
  "poll idea", "I have nothing to story about", or wants to sell something
  without making a post about it.
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


# ig-story

Stories are not a smaller feed. The feed is how strangers find you. Stories are
how the people who already follow you decide whether you are a person worth
buying from, and they are the only surface on Instagram where a tap turns into
a conversation in one move.

Nobody outside your followers sees these, so the job is completely different:
depth, not reach.

## The daily shape

Three to seven frames a day. Beyond about seven, the tap-forward rate climbs
and the last frames play to nobody, which is exactly where people put the ask.

```
1       THE OPEN     something happening today, with a face or a hand in it.
2-3     THE MIDDLE   the actual content: the process, the result, the mistake.
4       THE ASK      one sticker. Poll, question box, quiz or link.
5       THE CLOSE    the answer, the outcome, or tomorrow's setup.
```

Put the ask at frame 4, not frame 7. Completion drops with every tap and the
ask should be seen by the people who are still there.

## The stickers, and what each is actually for

| sticker | job | use when |
| --- | --- | --- |
| **Poll** | the cheapest tap there is | you want volume of response, not information |
| **Question box** | harvesting the exact words people use | you need content ideas or objections, verbatim |
| **Quiz** | teaching by letting them be wrong | there is a common misconception in the niche |
| **Slider** | vibe check | nothing important. Fun, low value |
| **Link** | the only clickable surface besides the bio | there is somewhere real to go |
| **Countdown** | a deadline people can subscribe to | a launch, a live, a close date |
| **Add yours** | reach beyond your followers, occasionally | the prompt is one anyone in the niche can answer |

The question box is the most undervalued one in the list. Every answer is a
caption, a Reel hook or a DM opener written in the audience's own words. Feed
them to `$ig-reel` as formula #16.

## Rules

- **A face or a hand in the first frame.** Text on a coloured background gets
  tapped through, and the first frame decides whether the rest get watched.
- **One idea per frame.** Reading a paragraph on a story is not a thing anyone
  does.
- **Keep text inside the middle.** On 1080x1920, nothing above y=250 or below
  y=1600. The profile row sits on top and the reply bar sits underneath.
- **Talk to one person.** "You" singular. Stories are the closest thing to a
  DM that is not one.
- **Do not repost your own feed post to stories with no comment.** It is the
  single most ignored frame on the platform. If you are pointing at a post, say
  what happened in the comments and why it is worth going back for.
- **Sell on stories, not in posts.** Three frames of context, one frame of
  offer, one frame of proof. That sequence sells more than a feed post about
  the same thing and costs you no reach.

## The DM funnel, done honestly

The sequence that works: a story that names a problem, a question box or a poll
that lets people say "that's me", and then a reply to each person who answered.
The conversation starts because they spoke first.

Automated keyword DM replies are a real, supported feature for professional
accounts, through Instagram's own tools and approved partners. Bulk DMing
people who did not interact is not, and it is what gets accounts restricted.
The rule is simple: **they act first, then you reply.**

## Output

The frames in order, each with what is on screen, what is said, and which
sticker, plus what to do with the answers:

```
STORIES  ·  Tuesday  ·  5 frames

1  [selfie, walking]      "Third refund request this year. Same reason."
2  [screen recording]     the clause, highlighted
3  [talking]              "Approval is a feeling. Delivery is a date."
4  [poll]                 "Have you been burned by a late approval?"  Yes / Not yet
5  [text on photo]        "Reply and I will send you the clause."

After: everyone who votes Yes gets a reply. That is the whole funnel.
```

Nothing is posted. The user posts it.
