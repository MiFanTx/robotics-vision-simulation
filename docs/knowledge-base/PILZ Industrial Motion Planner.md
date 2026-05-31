---
tags: [ros2, motion-planning, pilz, industrial]
---

# PILZ Industrial Motion Planner

## What it is
A MoveIt2 planning pipeline (`pilz_industrial_motion_planner`) that produces **deterministic**,
**predictable** robot motion. Unlike [[Sampling-Based Motion Planning|sampling-based planners]], it
doesn't randomly explore — it computes the motion analytically from a velocity profile. Same command
→ identical trajectory every time.

## Why it exists
Real factories need motion that is **repeatable and certifiable** — you can't have a robot taking a
different swooping path near humans/equipment each cycle. PILZ is the industrial-standard answer and
is what real UR (Universal Robots) cells use. Saying "I used the Pilz planner for predictable PTP
moves" is a stronger industry signal than "I tuned RRTConnect."

## How it works — three command types
- **PTP** (Point-to-Point) — joint-interpolated, fastest; for **free-space** moves. *(Replaces
  RRTConnect for my stages 1/5/9.)*
- **LIN** — straight Cartesian line (conceptually like [[Cartesian Path Planning]]).
- **CIRC** — circular arc through a defined waypoint.

```python
# pymoveit2 — select before the move
self.moveit2.pipeline_id = 'pilz_industrial_motion_planner'
self.moveit2.planner_id  = 'PTP'
```

## Trade-offs / caveats
- PILZ does **not route around obstacles** like a sampling planner — it computes the direct move and
  fails if it's blocked. Fine for a clear workspace.
- **Config gotcha:** PTP needs velocity & acceleration limits defined in `joint_limits.yaml`
  (`has_velocity_limits` / `has_acceleration_limits` + values), or planning fails.
- **Prerequisite:** the PILZ pipeline must be **loaded** by `move_group` — you can't select a planner
  that isn't loaded. Verify first:
  ```bash
  ros2 param list /move_group | grep -i pilz
  ```

## In my project (status)
Phase 2 NEXT step (decided 2026-06-01): replace RRTConnect with **PILZ PTP** on the free-space stages.
First action next session = verify the pipeline is loaded before editing `pick_place_controller.py`.

## Related
[[MoveIt2 and Planning Pipelines]] · [[Sampling-Based Motion Planning]] · [[Cartesian Path Planning]] · back to [[ROS Knowledge Base]]
