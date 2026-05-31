---
tags: [ros2, motion-planning, moveit]
---

# MoveIt2 and Planning Pipelines

## What it is
**MoveIt2** is the standard ROS2 motion-planning framework for manipulators. Its central node is
**`move_group`**, which holds the robot model, the planning scene (collisions), kinematics (IK/FK),
and one or more **planning pipelines**. You ask it "move the end-effector to this pose" and it
returns a collision-free trajectory for the controllers to execute.

## Why it exists
Manipulation needs a lot of machinery — IK, collision checking, trajectory time-parameterization,
multiple planner backends — wired together consistently. MoveIt2 bundles that so you describe *what*
you want (a goal pose / joint config) rather than *how* to compute the motion.

## How it works — pipelines and planner selection
A **planning pipeline** is a backend (a family of planners) that `move_group` loads at startup. Two
common ones:
- **OMPL** — sampling-based planners → see [[Sampling-Based Motion Planning]] (e.g. RRTConnect).
- **PILZ** (`pilz_industrial_motion_planner`) — deterministic industrial moves → see [[PILZ Industrial Motion Planner]].

You choose *which* pipeline + planner per request:
```python
# pymoveit2 — set before issuing the move
self.moveit2.pipeline_id = 'ompl'           # or 'pilz_industrial_motion_planner'
self.moveit2.planner_id  = 'RRTConnect'     # or 'PTP' / 'LIN' / 'CIRC' for PILZ
```
**Key rule:** you can only select a pipeline/planner that `move_group` actually **loaded**. Verify:
```bash
ros2 param list /move_group | grep -i pilz
ros2 param get /move_group planning_pipelines
```

## In my project
- The `pick_place_controller` sets `pipeline_id='ompl'`, `planner_id='RRTConnect'` at the node level.
- Phase 2 plan: keep [[Cartesian Path Planning|Cartesian (LIN-like)]] for straight stages, switch the
  free-space stages to [[PILZ Industrial Motion Planner|PILZ PTP]].
- **IK gotcha:** the group name in `kinematics.yaml` must exactly match the SRDF planning group
  (`ur_manipulator`), or the IK solver silently fails to register.

## Related
[[Sampling-Based Motion Planning]] · [[PILZ Industrial Motion Planner]] · [[Cartesian Path Planning]] · back to [[ROS Knowledge Base]]
