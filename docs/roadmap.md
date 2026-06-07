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

## Phase 2 — Motion quality ✅ COMPLETE (2026-06-08)

Pipeline paths are now intuitive and demo-ready. Clean 9/9-stage end-to-end run verified.

- [x] **Cartesian planning for straight-line stages** (LOWER, LIFT, LOWER_TO_TARGET) — `cartesian=True, fraction_threshold=0.95` using FK pre-grasp pose. Confirmed straight-line motion (2026-06-01).
- [x] **Pre-grasp joint config** — found manually; straight-line stages show no wrist wrap. Analytical computation from object pose is backlog.
- [x] **Hybrid free-space moves** (decided 2026-06-04, implemented 2026-06-05). OMPL for the adaptive reaches (`MOVING_TO_OBJECT`, `HOMING`/abort), **PILZ PTP for the known object→target move** (stage 5, sync `compute_ik` → PTP).
- [x] **Stage-5 PILZ self-collision fixed (2026-06-08).** Seeded `compute_ik` with current joints + `shoulder_pan += Δθ` (pick→place bearing) so KDL lands in the clean base-rotation basin. `[IK] delta` collapsed to `pan≈+π/2, wrist_3≈+π/2, rest≈0`; PTP plans + executes cleanly (gotcha #20).
- [x] **Reliable repeat execution** — 5 cycles without failure (2026-06-08).
- [x] **Gripper/attach latency fixed (2026-06-08)** — ~10s/stage → ~ms. `_wait_for_future` now self-spins instead of a passive poll the evicted MTE could never service (gotcha #21).
- [x] **Collision-scene lifecycle (2026-06-08)** — box added to the planning scene → attached to gripper (full-gripper `touch_links`) → detached+removed, so OMPL routes around it instead of knocking it (gotcha #22).
- [x] **Vision/geometry z-decoupling (2026-06-08)** — x,y from ArUco, z derived from known surface + box height; place reuses the grasp height so the box is set down, not driven into the floor.
- [x] **Defensive `success = False`** at top of stage loop to prevent stale reads (2026-06-03).
- **Known limitation (deferred to Phase 6):** Robotiq fingers flick/asymmetric on release — Gazebo Classic ignores URDF `<mimic>` joints. Cosmetic; not a motion-quality defect.

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
| Motion quality | ✅ Done | Clean 9/9 run verified. Hybrid OMPL/PILZ; stage-5 seed fix; gripper latency fixed; collision-scene lifecycle; vision/geometry z-decoupling. Only the mimic-joint flick remains (Phase 6). |
| Demo recording | ⏭️ Unblocked | Motion is demo-ready — Phase 3 next |
| README | ❌ Not started | |
| Advanced features | ❌ Not started | |

See `docs/backlog.md` for the detailed enhancement backlog.
