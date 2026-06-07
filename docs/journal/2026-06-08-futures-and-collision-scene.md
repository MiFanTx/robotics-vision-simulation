# 2026-06-08 — Futures self-spin fix, collision-scene lifecycle, vision/geometry z-decoupling

Long session. Started with the stage-5 PILZ self-collision still open; ended with a **clean
end-to-end run, all 9 stages `SUCCEEDED`**, plus three motion-quality fixes and a deep
correction to our executor mental model. Phase 2 motion quality is now essentially complete.

## What we did (in order)

1. **Stage-5 PILZ seed fix — verified.** Filled the scaffolded IK seed so KDL lands in the
   clean "base-rotation" basin instead of a contorted one. The place is the pick rotated ~90°
   about the base, so we seed `compute_ik` with the current joints + `shoulder_pan += Δθ`
   (`Δθ = atan2(tgt.y,tgt.x) − atan2(pick.y,pick.x)`). Result delta was exactly the prediction:
   ```
   [IK] delta = [1.569, -0.017, 0.007, 0.008, -0.0, 1.568]
                 pan     lift    elbow   wr1     wr2    wr3
   ```
   `pan ≈ +π/2`, middle joints ≈ 0 (so `upper_arm_link` never sweeps into the gripper → no
   self-collision), and **`wrist_3 ≈ +π/2`** — the non-obvious bit: a pure base rotation drags
   the EE yaw with it, so the wrist must add an equal turn to hold the gripper-down orientation
   fixed. PTP then planned + executed cleanly. Removed the temp `[IK]` diagnostic logs.

2. **Gripper/attach 10s latency → milliseconds.** Each gripper/attach/detach stage was costing
   ~10s. Root cause (see gotcha #21): `_wait_for_future` was a *non-spinning* poll that assumed
   the background MTE would complete the future — but pymoveit2 had already evicted our node from
   the MTE (it self-spins via the global executor). So every wait burned the full 5s timeout.
   `Attach result: None` was the tell (a completed `call_async` future returns a `Response`,
   never `None`). Fixed by making `_wait_for_future` **spin the node itself** (`rclpy.spin_once`),
   exactly like pymoveit2/`compute_fk` do. Verified:
   ```
   530.823 GRASPING → 530.828 Attach result: AttachLink_Response(success=True, ...) → 530.829 LIFTING  (~5 ms)
   536.306 PLACING  → 536.308 RETREATING  (~2 ms)
   ```
   Real response object, not `None` — proof the future actually completed.

3. **Collision-scene lifecycle (issue #2: OMPL knocked the box).** OMPL only avoids what's in
   MoveIt's *planning scene*; the Gazebo box was invisible to it, so the reach planned straight
   through and knocked it (gotcha #22). Added the box as a world `CollisionObject` before the
   reach, **attached** it to the gripper at GRASPING (with the **full gripper link set** as
   `touch_links` — fingertips alone left `robotiq_85_base_link↔aruco_box` flagged), and
   **detached + removed** it at PLACING. Also hardened the abort path: detach the scene object
   before the safe-home and make it a single attempt (`max_retries=1`) — previously it spun the
   doomed home 5×.

4. **Vision/geometry z-decoupling (place slam + grasp robustness).** The held box was being
   driven into the floor at LOWERING_TO_TARGET, jolting the gripper. Root cause: a **semantic
   mismatch** — pick converts object→TCP via an offset, but place fed `tgt_pos.z` straight to the
   TCP, and `tgt_pos.z` was *box-center* semantics. Bigger picture: ArUco's z (camera optical
   axis) is its noisiest axis, and we already *know* the box height and resting plane. So we now
   take **x,y from vision and derive z from geometry**: named `self.surface_z`/`self.box_height`
   constants → `box_center_z = surface_z + box_height/2`, grasp at the center, and place reuses
   the grasp z (`place_tcp_z = grasp_z + (place_surface_z − pick_surface_z)`, delta 0 today). The
   old `GRASP_Z_OFFSET = -0.04` margin hack is gone.

## Key decisions + rationale

- **Self-spin to drive futures, consistently.** We *reversed* gotcha #18's "never spin, poll
  instead" prescription — it was over-corrected and wrong for this node. The real rule: in a
  sequential blocking callback, self-spin to drive each future; never rely on the live MTE to
  complete a future, because pymoveit2 evicts the node from it. See the corrected KB note.
- **Decouple z from vision = a strength, not cheating.** Trusting a known prior over a noisy
  sensor axis is exactly the judgment to show in a vision portfolio; the vision pipeline (detect
  → TF2 → x,y,yaw) is still fully on display. Isolated behind named constants so markerless
  detection / multi-object / tables don't fight it later.
- **Mimic-joint flick is Phase 6, not a bug.** Deferred (see Backlog / Roadmap).

## Concepts learned (the big one)

The whole executor/spin/future model, end to end:
**node = worker with an inbox; executor = the engine that drains it; spin = run the engine;
Future = a claim ticket only the engine can stamp; one node has exactly one owner; pymoveit2
steals ownership by self-spinning the *global* executor (`add_node` evicts our node from the
MTE); so in a sequential blocking callback you must self-spin to drive your own futures.**
Also: `spin_once(node)` doesn't target a future — it pumps the whole node; the future completes
as a side effect because the *client* binds response→future. And async (`call_async`/
`*_async`) never touches the executor; only the *sync* helpers self-spin. async + MTE works for
event-driven nodes; a blocking state machine must self-spin.

## Bugs hit

- `Attach result: None` + 10s stages → non-spinning future wait timing out (gotcha #21).
- OMPL knocking the box → box not in planning scene (gotcha #22).
- `robotiq_85_base_link ↔ aruco_box` collision → `touch_links` only had fingertips.
- Box center z first too high (`obj_pos.z − GRASP_Z_OFFSET`, = top face), then too low
  (`obj_pos.z − 0.025`, double-counted the grasp offset), then hardcoded `0.025` (magic number)
  → finally derived `surface_z + box_height*0.5`.
- Place driving box into floor → semantic mismatch (TCP vs box-center z).

## ← NEXT (start here)

Phase 2 motion quality is **done and verified** (clean 9/9 run, gripper latency fixed, box
avoided + placed gently). Open, all **deferred not blocking**:

1. **Mimic-joint flick (Phase 6).** Robotiq fingers move asymmetrically/flick on release —
   Gazebo Classic + pinned `gazebo_ros2_control` v0.4.6 ignore URDF `<mimic>` joints. Fix =
   mimic plugin or dual-finger transmissions. *Confirm first:* does it flick on a bare
   open/close with no box? (If yes → purely mimic joints.)
2. **Abort path doesn't physically detach** (only MoveIt scene) — box stays welded in Gazebo on
   an abort. Backlogged.
3. **Phase 3 — demo & README.** Motion is now demo-ready; record launch→detect→pick→place→home.

Everything this session is **verified** except the mimic-joint root fix (deferred).
