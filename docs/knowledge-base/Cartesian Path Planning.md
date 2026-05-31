---
tags: [ros2, motion-planning, moveit, cartesian]
---

# Cartesian Path Planning

## What it is
Planning a motion where the **end-effector follows a straight line** in Cartesian (task) space,
rather than letting the planner choose any joint-space route. In MoveIt2 this is
`compute_cartesian_path` (exposed as `cartesian=True` in pymoveit2's `move_to_pose`).

## Why it exists
Some moves *must* be straight: lowering onto an object, lifting it vertically, retreating. A
[[Sampling-Based Motion Planning|sampling planner]] would arc or swoop between the two poses; for a
controlled descent you want a pure straight-line translation.

## How it works
- MoveIt interpolates between waypoints in small steps (~few mm) and solves **IK at every step**.
- It returns the **fraction** of the path it managed to solve (0.0–1.0). You set a threshold
  (e.g. `cartesian_fraction_threshold=0.95`) and treat anything below as a failure.
- Because it interpolates **position *and* orientation** at each step, the *start* orientation
  matters enormously.

## The key gotcha — read FK orientation first
If the arm arrives at pre-grasp in a slightly different orientation than your hardcoded target, IK
must correct orientation at *every* step and the path fails after ~10%. The fix:
> After the free-space move, call **`compute_fk`** to read the *actual* end-effector pose, then use
> *that* orientation as the Cartesian target → the descent becomes pure translation.

Pattern: `move_to_pose (free-space) → compute_fk → Cartesian move using the FK pose`.

## In my project
Stages 2/4/6 (`LOWERING_TO_OBJECT`, `LIFTING`, `LOWERING_TO_TARGET`) use `cartesian=True,
cartesian_fraction_threshold=0.95` against the FK-derived pre-grasp pose. Confirmed straight-line
motion in the end-to-end test — this half of Phase 2 is done.

## Related
[[MoveIt2 and Planning Pipelines]] · [[PILZ Industrial Motion Planner]] (its LIN command is the deterministic cousin) · [[Sampling-Based Motion Planning]] · back to [[ROS Knowledge Base]]
