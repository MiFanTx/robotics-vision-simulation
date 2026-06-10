# AGENTS.md — Robotics Vision Simulation

> Map, not encyclopedia. This file orients an agent (or a returning human) fast.
> Detail lives in the linked docs. If something here is wrong, fix it here first —
> this is the single source of truth.

## What this is

A **vision-guided pick-and-place** system in ROS2 + Gazebo — UR3e + Robotiq, simulation
only, no hardware. Built as an industrial-grade successor to the Dobot final project; that
original mission closed with Phases 1–2. The repo now serves as the **training ground** for
long-term ROS2/MoveIt2 mastery (Track A) — the known-good system gets deliberately deepened
one capability at a time. See `docs/roadmap.md` for the track structure.

- **Repo:** https://github.com/MiFanTx/robotics-vision-simulation
- **Workspace:** `~/Workspace/robotics-vision-simulation/ros2_ws/`
- **Packages:** `robotics_vision_sim` (nodes), `robotics_vision_sim_msgs` (interfaces)

## Current state (keep this honest)

Phases 1–2 are **complete** (core pipeline + motion quality), verified 2026-06-08: clean
9/9-stage run, 5 consecutive cycles. Hybrid OMPL/PILZ free-space moves, Cartesian
straight-line stages, stage-5 IK seeding, collision-scene lifecycle, and vision/geometry
z-decoupling all working. Only the cosmetic mimic-joint finger flick remains (deferred).

**Current: A1 — v1 closure** — harden the known-good system (vision/motion failure recovery,
graceful abort, physical detach-on-abort), then a v1 proof artifact (architecture diagram,
design-decisions doc, one clean recorded run, README pass). See `docs/roadmap.md` for the
A1–A4 track structure.

Detection uses **ArUco markers**. Markerless / VLA perception is later-track, not done.

## Architecture

```
camera_node → vision_pipeline_node → pose_estimation_node
                                          ↓
                                 task_manager_node  (RunTask action + staleness check)
                                          ↓
                                 pick_place_controller  (9-stage state machine)
                                          ↓
                                 MoveIt2 + ros2_control → Gazebo (UR3e + Robotiq 2F-85)
```

`pose_estimation_node` publishes the object pose in `base_link` on `/vision/object_pose`.

## Stack

ROS2 Humble · Ubuntu 22.04 · Gazebo Classic 11 · MoveIt2 · ros2_control ·
`gazebo_ros2_control` **v0.4.6 (pinned)** · IFRA LinkAttacher · pymoveit2 · OpenCV · TF2 ·
Python 3.10 (ament_python).

## Build / run / verify

```bash
# build (from the workspace root — never the repo root)
cd ~/Workspace/robotics-vision-simulation/ros2_ws
colcon build --packages-select <pkg> && source install/setup.bash

# launch the system (run from ros2_ws with install/setup.bash sourced)
ros2 launch robotics_vision_sim gazebo_ur3e.launch.py

# run one full pick-and-place
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"

# introspect when debugging
ros2 node list / ros2 topic list / ros2 topic echo /vision/object_pose
```

## Non-negotiables (full reasoning in `docs/gotchas.md`)

- **Edit `ros2_ws/src/` only — never `install/` or the root workspace.** When a change has no
  effect, the running code is the installed copy; rebuild and verify with grep.
- **`colcon build` is required** for world-file changes (they install to the share dir).
- **Stage by path: `git add src/`** — never `git add -A` (it commits `build/ install/ log/`).
- **rclpy action clients are async** — use `send_goal_async()` + `get_result_async()` with
  `spin_until_future_complete`. There is no synchronous `send_goal()`.
- **Before any Cartesian move, read the actual EE orientation via FK** and use it as the target,
  or the planner fails at ~10%.
- **Set `GAZEBO_MODEL_PATH` via `os.environ[]`** at the top of the launch file; unresolved
  `model://` URIs make Gazebo hang silently.

## Where things live

| Doc | Purpose |
|-----|---------|
| `docs/roadmap.md` | Current phases, status, what's next (living) |
| `docs/backlog.md` | Out-of-scope enhancements (living) |
| `docs/gotchas.md` | Bugs & hard-won rules — read before debugging |
| `docs/journal/` | Dated session logs |
| `docs/knowledge-base/` | Obsidian vault of ROS concept notes (learning record) — start at `ROS Knowledge Base.md` |
| `docs/system-setup.md` | Machine, drivers, env reference |
| `docs/workflow.md` | Daily start-up / remote-access workflow |

## Conventions

- Node pattern: `ReentrantCallbackGroup` (separate server/client groups) + `MultiThreadedExecutor(num_threads=4)`.
- Pre-grasp uses a taught joint config via `move_to_configuration` (standard industrial practice, not a hack).
- Minimal, targeted edits. Diagnose root cause before pivoting approach (see gotcha #3).
- When using a reference repo, read its `Installation.md` / `README.md` first.
