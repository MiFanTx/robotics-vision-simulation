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
- **No collision avoidance — this is the big one.** PILZ computes *one* straight line (in joint space
  for PTP) and collision-checks it; if that line is blocked it just **fails**. It cannot reroute the
  way a [[Sampling-Based Motion Planning|sampler]] does. Crucially, "blocked" includes the **middle**
  of the path, not just the endpoints: a PTP move between two valid configs can still sweep the arm
  through the floor or a self-collision in between. More planning time changes nothing — it's not a
  search. **So PTP is right for moves between *known, verified-clear* configs (home, taught via-points),
  and wrong for an adaptive reach to a sensed pose that must dodge obstacles** — there you need a
  sampler ([[Sampling-Based Motion Planning|OMPL]]) or taught waypoints.
- **It needs a joint goal.** PTP to a *pose* lets PILZ pick its own (maybe wrist-flipped) [[Inverse Kinematics|IK]]
  solution, whose straight interpolation can self-collide. Resolve the pose to a joint config yourself
  first (with a chosen IK seed), then PTP to that config.
- **Config gotcha:** PTP needs velocity & acceleration limits defined in `joint_limits.yaml`
  (`has_velocity_limits` / `has_acceleration_limits` + values), or planning fails.
- **Prerequisite:** the PILZ pipeline must be **loaded** by `move_group` — you can't select a planner
  that isn't loaded. Verify first:
  ```bash
  ros2 param list /move_group | grep -i pilz
  ```

## In my project (status)
**Wired in but blocked (2026-06-03).** Pipeline registered in the launch + loaded in `move_group`
(verified); controller default switched to PILZ/PTP; `MOVING_TO_OBJECT` resolves the pose to a joint
config via [[Inverse Kinematics|IK]] then PTPs to it. **Blocker:** the PTP reach from home to the pick
config dips through `ground_plane` mid-path (the no-avoidance caveat above, made real). Raising the
hover target to clear it instead breaks IK (seed/basin coupling). **Open decision:** taught **via-point**
(PTP home → fixed high "ready" config → short Cartesian descent) vs **hybrid** (OMPL for the adaptive
reach, PILZ PTP only for `HOMING` / taught-config moves). See gotchas #14–17 + the 2026-06-03 journal.

## Related
[[MoveIt2 and Planning Pipelines]] · [[Sampling-Based Motion Planning]] · [[Cartesian Path Planning]] · back to [[ROS Knowledge Base]]
