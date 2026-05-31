# CLAUDE.md

This file is the entry point for Claude Code. The project map and all conventions live in
**[AGENTS.md](./AGENTS.md)** — read it first.

## Read these before working

- **[AGENTS.md](./AGENTS.md)** — architecture, stack, build/run commands, non-negotiables.
- **[docs/gotchas.md](./docs/gotchas.md)** — hard-won rules. Read before debugging; append after fixing a bug.
- **[docs/roadmap.md](./docs/roadmap.md)** — current phase and what's next.
- **[docs/backlog.md](./docs/backlog.md)** — out-of-scope enhancements.

## How to work on this project

This is a **learning portfolio**, not a delivery target. The owner (Yide) is building ROS2/MoveIt2
skills for employment, and must be able to rebuild and explain every part from scratch. That
changes how you help:

- **Teach, don't just solve.** Prefer templates with `# TODO:` markers and hints over complete
  solutions for conceptual work (kinematics, control loops, perception). Explain the *why* before
  the code.
- **Split the work correctly.** Conceptual struggle → the owner does it. Pure friction (build
  config, package structure, environment errors) → fine to handle directly. New concept → show a
  worked example, then let the owner re-implement.
- **Diagnose before pivoting.** Find the root cause first; try the direct fix; try one alternative;
  only then change approach. A workaround that creates two sources of truth or hardcoded values is
  worse than the original bug. (See gotchas #3.)
- **Minimal, targeted edits.** Change only what's asked; preserve everything else.
- **Be honest about mistakes.** If earlier advice was wrong, say so plainly — don't gloss over it.
- **Stage by path** (`git add src/`, `git add docs/`), never `git add -A`. Commit after each logical fix.

## Skills

Project skills live in `.claude/skills/`:
- `ros-lessons-logger` — append a bug/lesson to `docs/gotchas.md` after a fix.
- `ros-session-journal` — write a dated session summary to `docs/journal/`.

Offer these proactively at the end of a debugging session or when a milestone is reached.
