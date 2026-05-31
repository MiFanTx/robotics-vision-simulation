---
tags: [ros2, motion-planning, ompl, algorithms]
---

# Sampling-Based Motion Planning

The OMPL family of planners (RRT, RRTConnect, RRT\*). They find paths by **randomly sampling** robot
configurations rather than reasoning about geometry analytically — powerful in high-dimensional joint
spaces, but with important quality trade-offs.

## RRT — Rapidly-exploring Random Tree
- Start a tree at the robot's current joint configuration.
- Repeatedly: sample a random config, find the nearest tree node, extend a branch toward the sample.
- When the tree reaches the goal region, return that path.
- **Property:** *probabilistically complete* — given enough time it finds a path if one exists.
  **Not optimal** — the path is whatever the random growth produced.

## RRTConnect — the fast two-tree variant
- Grows **two** trees: one from the start, one from the goal, biased toward each other.
- Stops at the **first** moment the two trees connect into a collision-free path.
- This is the default in many MoveIt setups (and in my project).
- **Consequence:** because it quits at first connection, *more planning time buys nothing* — it
  already stopped. And it samples in **joint space**, so a path that's short for the joints can look
  like a swooping, wrist-rolling mess for the end-effector. Different random seed → different path
  each run (non-deterministic).

## RRT\* — adds optimality via rewiring
- Same sampling, plus a **rewiring** step: each time a new node is added, check nearby nodes and
  reconnect them *through* the new node if that lowers their path cost.
- **Property:** *asymptotically optimal* — paths keep improving the longer it runs.
- This is why "plan longer → shorter path" is **true for RRT\*** but **false for RRTConnect**.

## Mental model
> Bushwhacking across a dark room: you reach out, step toward any opening, repeat until you hit the
> far wall. You get there, but the route zig-zags. That's RRTConnect. RRT\* is the same hiker who
> keeps backtracking to straighten the route whenever a shortcut appears.

## In my project
The free-space moves (`MOVING_TO_OBJECT`, `MOVING_TO_TARGET`, `HOMING`) use RRTConnect and looked
inefficient/non-repeatable. Considered switching to RRT\* (better but still random + needs a time
budget); chose [[PILZ Industrial Motion Planner|PILZ PTP]] instead for *deterministic* motion. For
the short straight stages I use [[Cartesian Path Planning]], not a sampling planner at all.

## Related
[[MoveIt2 and Planning Pipelines]] · [[PILZ Industrial Motion Planner]] · [[Cartesian Path Planning]] · back to [[ROS Knowledge Base]]
