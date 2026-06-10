# Project Roadmap — Track A (The Arm)

Living roadmap for the robotics-vision-simulation project. Update as it evolves.

> **Reframed 2026-06-10.** This project is no longer a hiring portfolio with a finish line.
> The original mission — *a better, industrial version of the Dobot final project* — was
> achieved when Phases 1–2 closed. The repo now serves as the primary **training ground**
> on the long-term mastery track: the known-good system that gets deliberately deepened,
> hardened, and upgraded one capability at a time.
>
> **Metric:** learning value per hour. **Proof** (documentation, explainable demos) is the
> exhaust, never the goal — written for depth-on-demand (survives a robotics engineer's
> questions), not for HR skimmability.
>
> This roadmap covers Track A only. The two-track frame (Track B = embedded/physical,
> rhythm, review cadence) lives in `master-plan.md` in the personal meta-repo.

**Repo:** https://github.com/MiFanTx/robotics-vision-simulation

---

## Completed foundation

- **Phase 1 — Core pipeline ✅** (see git history / journal): UR3e + Robotiq in Gazebo,
  ArUco vision pipeline, TF2 pose transform, 9-stage pick-place state machine,
  RunTask orchestration. One `ros2 action send_goal` runs the whole system.
- **Phase 2 — Motion quality ✅ (2026-06-08):** Cartesian straight-line stages, hybrid
  OMPL/PILZ free-space moves, stage-5 IK seeding, self-spin wait discipline,
  collision-scene lifecycle, z-decoupling. Clean 9/9 run, 5 consecutive cycles.

## A1 — v1 Closure 🎯 CURRENT (~1.5–2 weeks at current capacity)

Harden the known-good system, then formally close v1. *Done = the repo could be handed
to a robotics engineer and survive their questions.*

Robustness (old Phase 3, kept — error recovery is core systems engineering):

- [ ] **Vision failure handling** — on stale `/vision/object_pose`, wait + retry detection
  (configurable count/timeout) instead of aborting.
- [ ] **Motion failure recovery** — safe home before abort; joint-space home fallback that
  bypasses Cartesian.
- [ ] **Graceful abort from any stage** — cancel always ends in a safe home, never a frozen arm.
- [ ] **Physically detach on abort** — clear the LinkAttacher weld, not just the MoveIt scene.

v1 proof artifact (technical write-up, not marketing):

- [ ] **Architecture diagram** — the node pipeline.
- [ ] **Design-decisions doc** — the *whys*: stage-5 IK seeding, self-spin discipline,
  z-decoupling, hybrid planner split, pinned `gazebo_ros2_control`.
- [ ] **One clean recorded run** — launch → detect → pick → place → home.
- [ ] **README pass** — overview, setup, links into the above. Depth-on-demand, minimal polish.

> Closing A1 unlocks Track B (embedded project) as the weekend hands-on lane.

## A2 — VLA Probe ⏳ NEXT (time-boxed: ~4 sessions, hard stop)

Calibration, not product: puncture the "can I do cutting-edge?" doubt with a measured answer.

- [ ] **SmolVLA via LeRobot** — pretrained inference on the LIBERO sim benchmark (feasible
  on the 3060 Ti: 450M params, inference fits easily in 8 GB).
- [ ] **One small fine-tune** — reduced batch (~16–24); learn the imitation-learning
  workflow end to end: dataset → policy → eval.
- [ ] **Write-up** — what worked, what the hardware ceiling actually is, whether a second
  VLA experiment belongs in A4. Knowledge-base notes for the concepts.

Hard stop after the time box regardless of outcome — findings feed the next review.

## A3 — Deep Control Chain (open-ended; the centerpiece)

The deterministic industrial planning chain used in real UR deployments. Promoted from
old Phase 6: the engineering cost *is* the learning. Socratic mode; implementations owned,
not delegated.

- [ ] **TRAC-IK (or Bio-IK) as KDL replacement** — repeatable configs near workspace
  boundaries; configure under `ur_manipulator` in `kinematics.yaml`.
- [ ] **Full PILZ** — PTP + LIN everywhere applicable; add `config/pilz_cartesian_limits.yaml`
  (currently missing — LIN needs it).
- [ ] **Trajectory smoothing / time-parameterisation** — compare against the OMPL baseline.
- [ ] **Skip-retry on deterministic planner failures** (backlog item — pull in here).

## A4 — Perception upgrades (optional; decide at the A3 review)

Kept because they're genuinely wanted improvements, demoted from "headline" status.

- [ ] Yaw-aware grasp orientation (RPY decompose, keep yaw + fixed downward pitch)
- [ ] Orientation / object detection beyond ArUco — possibly merged into a second VLA
  experiment instead of a standalone YOLO/FoundationPose swap. Re-decide then.

## Deferred (unsequenced — pull in only if it becomes the highest-learning item)

Mimic-joint fix, camera URDF integration, on-demand detection service, target-pose
detection, multi-object, proper SDF model, hand-eye calibration, sim→real transfer guide.
Detail stays in `docs/backlog.md`.

---

## Status summary

| Block | Status | Notes |
|-------|--------|-------|
| Phases 1–2 (pipeline + motion) | ✅ Done | Original mission complete |
| A1 — v1 closure | 🎯 Current | Robustness + proof artifact; gates Track B |
| A2 — VLA probe | ⏳ Next | Time-boxed calibration experiment |
| A3 — deep control chain | ❌ Not started | TRAC-IK → PILZ → smoothing |
| A4 — perception | ⏸️ Optional | Decided at A3 review |

Review cadence and cross-track rhythm: see `master-plan.md`.
