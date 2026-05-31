---
name: ros-lessons-logger
description: >
  Log mistakes, bugs, and lessons learned from ROS (Robot Operating System) project work into the
  repo's docs/gotchas.md file. Use this skill whenever: Claude notices it made a mistake or gave
  wrong advice; the user explicitly says Claude did something wrong; a bug is resolved after
  debugging back-and-forth; or any debugging session concludes. Do NOT wait to be asked —
  proactively offer to log the lesson at the end of any bug fix or correction.
  The goal is a growing, version-controlled knowledge base that makes future sessions better.
---

# ROS Lessons Logger

Append mistakes and lessons to `docs/gotchas.md` in the repo so hard-won knowledge is never lost
and lives in version control alongside the code.

**Location:** `docs/gotchas.md` in the repo (`~/Workspace/robotics-vision-simulation/`).

## When to use

Trigger proactively when:
- Claude gave incorrect advice that had to be corrected
- A bug was found and fixed (especially after back-and-forth)
- The user says "you did something wrong" or similar
- A debugging session concludes with a resolution
- Claude self-notices an error mid-conversation

Say: "Want me to log this as a lesson in `gotchas.md`?"

---

## Entry format

`gotchas.md` entries lead with the **actionable rule**, then the reasoning, then a transferable
principle. Match the existing numbered style in the file:

```markdown
---

### N — [Short rule, imperative: e.g. "Specify reliable QoS for sensor subscriptions"]
*YYYY-MM-DD*

[1–3 sentences: the root cause — what assumption was wrong, what was misunderstood, what edge case
was missed.]

- [concrete action item to prevent recurrence]
- [another, if needed]

**Principle:** [1–2 sentences — the generalizable rule of thumb that applies beyond this bug.]
```

Keep it tight. Be specific: "Always pass ArUco args as keywords" beats "be careful with ArUco".

---

## Steps

### Step 1: Open gotchas.md and find the next number
Read `docs/gotchas.md`. Find the highest existing `### N` heading; the new entry is `### N+1`.
If the file doesn't exist yet, create it with the standard header and start at `### 1`.

### Step 2: Compose the lesson
From the conversation, draft the rule heading, the root-cause sentences, the prevention bullets,
and the principle. Show the draft in chat: "Does this look right, or anything to adjust?"

### Step 3: Append
Append the new entry to the bottom of `docs/gotchas.md` — never overwrite existing entries.
- If a filesystem/editing tool for the repo is available, edit the file directly.
- Otherwise, output the entry block in a code block and ask the user to paste it at the bottom.

Confirm: "Gotcha #N logged to `docs/gotchas.md`. Remember to commit (`git add docs/ && git commit`)."

---

## Style

- Write as if future-Claude reads this cold, with no memory of the session.
- The rule heading should be directly actionable; the principle should generalize.

## Notes

- Everything is local markdown in the repo — no Notion, no external service.
- `gotchas.md` is also referenced from `AGENTS.md`, so logged rules become agent guidance
  automatically — every new entry strengthens the harness.
- Companion skill `ros-session-journal` handles full session summaries in `docs/journal/`.
