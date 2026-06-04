---
description: End-of-session save ritual — journal, gotchas, backlog, roadmap, knowledge base, memory, logs, commit
---

Run the full end-of-session save for this repo. Do every step, then report a short checklist of
what was written. Skip a step only if there is genuinely nothing new for it, and say so.

1. **Capture the run logs (read, don't commit).** Read `/tmp/ros_run.log` and the newest
   `~/.ros/log/move_group_*.log` for the diagnostic detail, and **embed only the key excerpts**
   (errors, stats, IK deltas) into the journal. Do **not** copy raw logs into the repo — they're
   reproducible bloat (`docs/journal/*.log` is gitignored). The journal excerpt is the durable record.

2. **Journal.** Write/append `docs/journal/$(date +%F)-<slug>.md`: what we did, key decisions +
   rationale, concepts learned, bugs hit, and an explicit **← NEXT (start here)** section with the
   concrete next step and whether it's verified.

3. **Gotchas.** Add any new hard-won rule to `docs/gotchas.md` (next number in sequence), or extend
   an existing one. Lead with the symptom, then the mechanism, then the fix/principle.

4. **Backlog.** File out-of-scope or deferred-proper-fix items in `docs/backlog.md`.

5. **Roadmap.** Update `docs/roadmap.md` phase status + the status-summary table to match reality.

6. **Knowledge base (Obsidian).** For each genuinely new concept, add/extend an atomic note in
   `docs/knowledge-base/` (what it is → why → how → how it showed up here; link with `[[wikilinks]]`)
   and update the index `docs/knowledge-base/ROS Knowledge Base.md`.

7. **Auto-memory.** Update `~/.claude/projects/-home-yide-Workspace-robotics-vision-simulation/memory/`:
   refresh the project state memory, add new feedback/reference memories, and update `MEMORY.md`.
   Prefer updating an existing file over creating a duplicate.

8. **Commit.** Stage by path (`git add src/ docs/ CLAUDE.md AGENTS.md .claude/` — **never** `git add -A`,
   it commits `build/ install/ log/`; see gotcha #5). Write an honest commit message (mark WIP if the
   work is unverified). End the message with the Co-Authored-By trailer. Do **not** push unless asked.

9. **Report.** Print a one-line-per-item checklist of what was saved and the commit hash.

Conventions: this is a *learning* project — favour the "why" in every artifact. Never reference
Notion. Reference the UR3e sim architecture, never the legacy Dobot system.
