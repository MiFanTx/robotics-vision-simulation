# Learning Journal

Session-by-session learning log. One file per session: `YYYY-MM-DD-short-topic.md`.

Each entry has a 2–4 sentence big-picture summary, then four bulleted sections:

- **What we built** — tasks, files, commands; what now works that didn't before.
- **Concepts learned** — ROS/robotics concepts: what, why they exist, how they fit. Write for a future-you who forgot.
- **Code & commands** — key snippets with a short explanation of what and why.
- **Design decisions & rationale** — why this approach, what alternatives, what constraints drove it.

Bugs and mistakes go in `../gotchas.md`, not here.

## Index

<!-- Add a line per session, newest at top -->
- [2026-06-03 — Wiring in PILZ PTP, and hitting its real limit](2026-06-03-pilz-ptp-integration.md) — PILZ pipeline loaded + controller switched to PTP; `MOVING_TO_OBJECT` rebuilt to async-IK→joint-config; hit the PTP no-avoidance limit (path dips through floor) + KDL seed/budget fragility. Checkpointed at the via-point vs hybrid fork.
- [2026-06-01 — RRTConnect vs PILZ](2026-06-01-rrtconnect-vs-pilz.md) — re-oriented, confirmed pipeline runs end-to-end, diagnosed inefficient free-space motion as RRTConnect, chose PILZ PTP as the fix.
- _(migrate dated entries from the old Notion "ROS Learning Journal" here)_
