# Project Roadmap

Living roadmap for the robotics-vision-simulation portfolio project. Update as it evolves.

**Goal:** a demo-ready, portfolio-quality vision-guided pick-and-place system in ROS2/Gazebo
demonstrating industry-standard skills to employers.
**Repo:** https://github.com/MiFanTx/robotics-vision-simulation

---

## Phase 1 — Core pipeline ✅ COMPLETE

End-to-end built and connected.

- [x] UR3e + Robotiq 2F-85 gripper in Gazebo Classic
- [x] Camera node + ArUco detection (`vision_pipeline_node`)
- [x] TF2 pose transform camera → base_link (`pose_estimation_node`)
- [x] 9-stage pick-and-place state machine with MoveIt2 (`pick_place_controller`)
- [x] Task orchestrator with RunTask action + staleness check (`task_manager_node`)
- [x] One `ros2 action send_goal` runs the whole pipeline

```bash
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"
```

## Phase 2 — Motion quality 🔧 NEXT

Pipeline works but paths are non-intuitive. Fix before recording demos.

- [x] **Cartesian planning for straight-line stages** (LOWER, LIFT, LOWER_TO_TARGET) — `cartesian=True, fraction_threshold=0.95` using FK pre-grasp pose. Confirmed straight-line motion in end-to-end test (2026-06-01).
- [x] **Pre-grasp joint config** `[0.1, -0.8, 0.75, -1.4, -1.6, 0.0]` — found manually (gripper directly above box); straight-line stages show no wrist wrap. Analytical computation from object pose is backlog. (RViz tuning N/A — `ur_moveit_config` doesn't know the Robotiq gripper, so RViz is skipped.)
- [~] **Hybrid free-space moves (decided 2026-06-04, implemented 2026-06-05).** OMPL for the adaptive reaches (`MOVING_TO_OBJECT` stage 1, `HOMING`/abort stage 9), **PILZ PTP for the known object→target move** (stage 5). Stage 1 is plain OMPL `move_to_pose`; stage 5 resolves the place pose → a joint config via **sync** `compute_ik` then PTP; homing resets to OMPL (9a/9b done). Getting the run to reach stage 5 required killing a deep rclpy executor bug — node-spinning sync calls corrupt `node.executor` and silently kill the lazily-created IK client (gotcha #18, KB [[ROS2 Executors, Threads and Spinning]]).
  - **← NEXT: stage-5 self-collision.** PILZ PTP is rejected as a self-collision (`robotiq_85_left_finger_link` ↔ `upper_arm_link`). The place is geometrically a ~90° base rotation of the pick (same radius/height), but KDL returns a contorted IK config that PTP sweeps through the arm (gotcha #20). **Fix scaffolded, unverified:** seed `compute_ik` with the current joints + base pre-rotated by the pick→place angle. If it still collides → taught via-point. See the 2026-06-05 journal and gotchas #18–20.
- [ ] **Reliable repeat execution** — 5 cycles without failure.
- [x] **Defensive `success = False`** at top of stage loop to prevent stale reads — set at the top of each stage iteration (`pick_place_controller.py`); confirmed by the clean abort/safe-home on IK and planning failures (2026-06-03).

## Phase 3 — Demo & portfolio polish

- [ ] **README** — overview, architecture diagram, setup, demo GIF/video (60-second understanding).
- [ ] **Demo recording** — launch → detect → pick → place → home, no errors, smooth motion.
- [ ] **Architecture diagram** — the node pipeline.
- [ ] **Code cleanup** — remove debug logs, add docstrings, consistent style.
- [ ] **Repo polish** — `.gitignore`, clean history, tags/releases.

## Phase 4 — Error recovery

- [ ] **Vision failure handling** — on stale `/vision/object_pose`, wait + retry detection (configurable count/timeout) instead of aborting.
- [ ] **Motion failure recovery** — safe home before abort; add a joint-space home fallback that bypasses Cartesian.
- [ ] **Graceful abort from any stage** — cancel always ends in a safe home, never a frozen arm.

## Phase 5 — Advanced features (stretch)

**High value**
- [ ] Yaw-aware grasp orientation (extract yaw from ArUco, keep fixed gripper-down pitch)
- [ ] Markerless detection (YOLO or FoundationPose)
- [ ] On-demand detection service (topic → callable service)

**Medium value**
- [ ] Target pose detection (dynamic place location)
- [ ] Multi-object handling
- [ ] Proximity-based grasp validation

**Lower priority**
- [ ] Proper SDF object model (realistic mass/inertia)
- [ ] Hand-eye calibration node
- [ ] Real hardware transfer guide

## Phase 6 — Simulation fidelity

- [ ] **Gripper mimic joints** — Robotiq closes asymmetrically in Gazebo Classic (mimic joints ignored). Add ros2_control transmissions for both fingers or a mimic plugin.
- [ ] **Camera URDF integration** — define camera as a link in the robot URDF so `robot_state_publisher` publishes its TF; removes the SDF + manual `camera_tf_broadcaster` two-source problem.
- [ ] **TRAC-IK or Bio-IK** — replace KDL; fewer wrist flips, more repeatable configs.
- [ ] **PILZ Industrial Planner** — PTP (free-space) + LIN (straight-line), fully deterministic. Requires TRAC-IK first.
- [ ] **Trajectory smoothing** — OMPL post-processing as an intermediate step before PILZ.

---

## Status summary

| Component | Status | Notes |
|-----------|--------|-------|
| Simulation (Gazebo + UR3e) | ✅ Done | Gripper, controllers, LinkAttacher working |
| Vision pipeline | ✅ Done | ArUco, TF2 transform, `/vision/object_pose` |
| Pick-place controller | ✅ Done | 9 stages, MoveIt2, gripper, attachment |
| Task manager | ✅ Done | RunTask action, staleness check, feedback |
| Motion quality | 🔧 In progress | Hybrid done (OMPL stages 1/9, PILZ stage 5); executor bug fixed. Stage-5 PILZ blocked on a self-collision from a contorted KDL IK config — seed fix scaffolded, unverified. |
| Demo recording | ❌ Not started | Blocked on motion quality |
| README | ❌ Not started | |
| Advanced features | ❌ Not started | |

See `docs/backlog.md` for the detailed enhancement backlog.
