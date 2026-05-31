---
name: ros-session-journal
description: >
  Write a structured ROS learning session summary as a dated markdown file in the project repo
  under docs/journal/. Captures: what was built, ROS/robotics concepts learned, key code and
  commands with explanations, and design rationale — all in bullet points with a brief
  big-picture summary at the top.

  Trigger whenever: user says "summarise today", "log this session", "update my journal", or
  similar. Also proactively offer when the session is wrapping up or a milestone is reached
  (first working node, new concept mastered, launch file built). Do NOT wait to be asked —
  offer with "Want me to write a session summary in your journal?"

  For bugs and mistakes only, use ros-lessons-logger instead. This skill is for the full
  session-level learning journal.
---

# ROS Session Journal

Capture each ROS learning session as a rich, structured markdown file in the repo — so the
project's full history, reasoning, and concepts live in version control and are never lost.

**Location:** `docs/journal/YYYY-MM-DD-short-topic.md` in the repo
(`~/Workspace/robotics-vision-simulation/`). Index file: `docs/journal/README.md`.

---

## When to trigger

**Proactively offer** when:
- The user signals the session is ending ("ok that's it for today", "let's stop", "I'm done")
- A significant milestone is reached (first working node, successful launch, new concept mastered)

**Always trigger** when the user directly requests it: "summarise today's session", "log what we
did", "update my journal", "write a session summary".

Say something like: "Want me to write a session summary into your journal?"

---

## What each entry captures

Every entry has four sections:

1. **What We Built** — Tasks completed, files created, commands run. What now works that didn't before.
2. **Concepts Learned** — ROS/robotics concepts encountered: what they are, why they exist, how
   they fit the bigger picture. Write for a future-you who has forgotten the details.
3. **Code & Commands** — Key snippets, configs, or commands, each with a short explanation of
   what it does and why it was written that way.
4. **Design Decisions & Rationale** — Why this approach? What alternatives were considered? What
   constraints or ROS conventions drove the decision?

---

## Writing style

- **All four sections use bullet points** — no prose paragraphs.
- Long bullets (2–4 sentences) are fine and encouraged. The goal is clarity, not brevity.
- Use inline code formatting for all node names, topics, files, commands, and code.
- Explain the *why* inside the bullet. Good: "Used `std_msgs/String` instead of a custom message —
  custom messages add CMake complexity and a rebuild cycle on every schema change, unnecessary
  until we have real typed data." Bad: "Used String message type."
- Write for future-Yide reading this cold, months from now.

## File format

```markdown
# YYYY-MM-DD | Session Topic

[2–4 sentences. Big picture only — the main goal, what was achieved, and the key idea that
anchors the session. No detail, no bullets.]

## What We Built
- [specific task, file, or outcome — include what now works]

## Concepts Learned
- **[concept]**: [what it is, why it exists, how it fits — long bullets OK]

## Code & Commands
- `command or snippet` — [what it does and why used this way]

## Design Decisions & Rationale
- [decision] — [why, alternatives considered, constraints]
```

---

## Steps

### Step 1: Review the conversation
Scan the full session for: every file created/modified, every ROS concept mentioned (topics,
nodes, services, params, YAML, launch files, QoS…), every command run, and every point where one
approach was chosen over an alternative. Don't skip things that felt minor.

### Step 2: Draft the summary
Write all four sections. Show the draft in chat first: "Here's today's summary — anything missing
or to adjust before I save it?"

### Step 3: Get confirmation
Wait for the user to confirm or request edits. Apply changes.

### Step 4: Save the file
Write `docs/journal/YYYY-MM-DD-short-topic.md` with the format above. Use today's date and a short
kebab-case topic (e.g. `2026-03-10-first-publisher-subscriber.md`).
- If a filesystem/editing tool for the repo is available, create the file directly.
- Otherwise, output the full file content in a code block and ask the user to save it at that path.

### Step 5: Update the index
Add a line to `docs/journal/README.md` under "## Index" (newest at top), linking the new file:
`- [YYYY-MM-DD | Topic](./YYYY-MM-DD-short-topic.md)`.

Confirm: "Session logged — `docs/journal/<file>` created and indexed. Remember to commit (`git add docs/ && git commit`)."

---

## Notes

- Everything is local markdown in the repo — no Notion, no external service.
- Never overwrite existing entries; each session is its own file.
- Companion skill `ros-lessons-logger` handles bug/mistake entries in `docs/gotchas.md`. If a bug
  was fixed this session, offer to log it there too after the journal entry is done.
