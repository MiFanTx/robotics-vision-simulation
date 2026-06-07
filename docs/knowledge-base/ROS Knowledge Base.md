---
tags: [ros2, moc, index]
---

# ROS Knowledge Base

Map of Content (MOC) for my ROS2 / robotics learning. Each linked note is **atomic** — one
concept, written for a future-me who forgot. Built from things learned while building the
[vision-guided pick-and-place project](../../AGENTS.md). Open this folder as an Obsidian vault.

> Convention: one concept per note · link liberally with `[[wikilinks]]` · lead with *what it is*
> and *why it exists*, then *how it works*, then *how it showed up in my project*.

## Motion planning
- [[MoveIt2 and Planning Pipelines]] — the framework + how it picks a planner
- [[Sampling-Based Motion Planning]] — RRT, RRTConnect, RRT\* (the OMPL family)
- [[PILZ Industrial Motion Planner]] — deterministic PTP / LIN / CIRC (and why it can't dodge obstacles)
- [[Cartesian Path Planning]] — straight-line end-effector motion
- [[Inverse Kinematics]] — pose → joint angles; KDL's seed/budget fragility, TRAC-IK
- [[MoveIt Planning Scene and Collision Objects]] — the planner's world model (≠ Gazebo); collision-object lifecycle, touch_links

## Perception
- [[ArUco Marker Detection]] — fiducial markers, two-stage detection, pose estimation

## ROS2 core
- [[ROS2 Workspaces and Sourcing]] — colcon, overlays, why you `source` every terminal
- [[ROS2 Actions]] — long-running goals, the async client pattern
- [[ROS2 Executors, Threads and Spinning]] — executor vs threads; futures as claim tickets; why pymoveit2 evicts your node from the MTE, so you must self-spin to drive your own futures
- [[ROS2 Introspection and Debugging Tools]] — the CLI tools for seeing what's running

## How these connect
The project pipeline is: a camera frame → [[ArUco Marker Detection]] → an object pose → a
[[ROS2 Actions|RunTask action]] → a state machine that plans motion with [[MoveIt2 and Planning Pipelines|MoveIt2]],
using [[Cartesian Path Planning]] for straight descents. Free-space moves are **hybrid**: OMPL
([[Sampling-Based Motion Planning|RRTConnect]]) for the adaptive reaches, [[PILZ Industrial Motion Planner|PILZ PTP]]
for the known object→target move (which needs an [[Inverse Kinematics]] joint goal, seeded into the right
basin). The grasped object is mirrored into the [[MoveIt Planning Scene and Collision Objects|planning scene]]
so OMPL routes around it, and every wait in the action callback self-spins the node
([[ROS2 Executors, Threads and Spinning]]) because pymoveit2 evicts it from the executor.
