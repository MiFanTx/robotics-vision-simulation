# 2026-06-05 — The executor-corruption rabbit hole, and the real PILZ collision underneath

Long, deep session. Goal was to finish the Phase-2 hybrid (OMPL for the adaptive reach, PILZ
PTP for the known object→target move) and prove PILZ in the loop. Got there conceptually, but
the path went through a multi-layer rclpy executor bug that masked the actual motion problem.
Ended with the real problem isolated (a self-collision from a contorted IK solution) and the
fix scaffolded but not yet verified.

## Decision locked: hybrid (B)
- **Stage 1 `MOVING_TO_OBJECT` → pure OMPL** `move_to_pose` (no IK dance — OMPL samples IK and
  routes around the floor itself). Yide implemented this.
- **Stage 5 `MOVING_TO_TARGET` → IK→joint-config + PILZ PTP** (the stage that proves PILZ).
- **Stage 9 `HOMING` + abort safe-home → reset to OMPL** (homing from an arbitrary/failed pose
  is adaptive; must route around the floor, not blind-PTP through it).
- Rationale (Yide's): PILZ gives a deterministic line that may collide and is unsuitable for an
  adaptive reach to a sensed pose; reserve it for known→known moves.

## The executor bug (the big lesson — see KB note [[ROS2 Executors, Threads and Spinning]])
Stage-5 `compute_ik` hung forever (`future is not done`, 5 s timeout) — but only *after* GRASPING.
Chasing it taught the whole executor model:

1. **`rclpy.spin_until_future_complete(self, future)` corrupts the node.** It grabs the global
   `SingleThreadedExecutor`, `add_node(self)` reassigns `node.executor` to it, and `remove_node`
   never restores it. The node's "who's my executor" pointer is left dangling at the idle global
   executor. (rclpy `__init__.py:252-259`, `executors.py:283-285`.)
2. **`wait_until_executed()` does the same** via `rclpy.spin_once` (pymoveit2 `moveit2.py:790`) —
   so the corruption actually happens back in **stage 1**, on every motion, not just GRASPING.
3. **The damage is dormant.** It only bites the *next lazily-created* client: that client's
   wait-set registration goes to the dead executor, so the live MTE never services its future.
   Clients created in `__init__` (gripper/attach/detach) survive — which is why everything *else*
   worked and only the lazily-created stage-5 IK client died.
4. **Why `compute_fk` (sync) always worked but our async IK didn't:** sync calls `spin_once` the
   node *themselves* to drive their own future (they don't depend on the MTE). Our async
   `compute_ik_async` + passive poll depends on the MTE seeing a cleanly-registered client.

**Proven with a probe:** a `compute_ik` at the very top (before any spin) made stage-5 IK work —
because the client was created pre-corruption.

**Fixes applied:**
- Replaced the four `rclpy.spin_until_future_complete(self, future)` (GRASPING/PLACING) with a
  non-spinning `_wait_for_future()` poll helper.
- Switched stage-5 IK to **sync `compute_ik`** (self-spins like `compute_fk` → immune to the
  corruption). This is what finally got past the hang. (Contradicts gotcha #16's blanket "don't
  use sync compute_ik" — that crash needs *concurrent* spinning, which our serial single-callback
  flow doesn't have; `compute_fk` proves sync-spin is safe here.)
- Proper root fix (backlogged): replace `wait_until_executed()` with a non-spinning
  `query_state()` poll so nothing ever spins the node.

## The real problem underneath: stage-5 self-collision
With IK working, stage 5 reached PILZ — which **rejected the path as self-colliding**:
`robotiq_85_left_finger_link` ↔ `upper_arm_link`. The geometry says it shouldn't be hard:

| | radius from base | base angle | height |
|---|---|---|---|
| Pick (EE) | 0.448 m | 26.7° | 0.080 |
| Place (EE)| 0.447 m | 116.6° | 0.075 |

**The place is the pick rotated ~90° about the base, same radius, same height.** The ideal move
is "rotate the base 90°, freeze the rest." But the `[IK] delta` instrumentation showed KDL
returned a **wildly contorted** config instead:
```
delta = [+5.303, +3.982, +0.011, -7.135, -3.141, +2.162]   # want ≈ [+1.57, 0,0,0,0,0]
```
base swings 300°+, wrist_1 more than a full turn. PTP linearly blends that → nearly the whole
path collides (indices 14–63/78). KDL is local and jumped to a far IK basin from the cold seed
(start config has ugly wrist angles ~257°/270°). Gotcha #15 at full volume.

## Collision stats method (reusable)
Read `~/.ros/log/move_group_*.log`, count contact pairs, **separate by failing move** (don't
aggregate — the raw "ground_plane wins 185/210" was the *homing* dip, a different move; the
stage-5 move is the gripper↔upper_arm self-collision). Two distinct `Invalid states` signatures =
two distinct moves.

## Log-reading workflow established (no more copy-paste)
- Run with `... 2>&1 | tee /tmp/ros_run.log`; I read `/tmp/ros_run.log`.
- Zero-setup fallback: `~/.ros/log/<node>_*.log` (per-node, complete, never truncated by
  scrollback). `move_group_*.log` is the gold one for planning failures.

## Housekeeping fixed
- Detached HEAD → reattached to `main` (no work lost).
- Accidental `colcon build` in the **repo root** created stray `build/ install/ log/` (not
  gitignored) and poisoned `AMENT_PREFIX_PATH` → `get_package_share_directory` resolved to an
  incomplete install → camera `model://` unresolved → **Gazebo silently dropped the camera**.
  Deleted the stray dirs; reinforced build+source from `ros2_ws` only (gotcha #19).

## ← NEXT (start here)
1. **Finish the seed fix** in stage 5 (scaffolded): `import math`; build `seed` = current joints
   with `shoulder_pan += atan2(tgt.y,tgt.x) - atan2(pick.y,pick.x)`; pass `start_joint_state=seed`
   to `compute_ik`. Re-run; the `[IK] delta` should collapse to small, non-colliding values and
   PILZ should plan + execute. **This is unverified.**
2. If the seed still gives a colliding solution → escalate to a **taught via-point**.
3. Then: remove the `[IK]` diagnostic logs, run 5 clean cycles, update roadmap.

See gotchas #18–20, backlog, and KB [[ROS2 Executors, Threads and Spinning]].
