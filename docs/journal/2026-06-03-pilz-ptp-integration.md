# 2026-06-03 — Wiring in PILZ PTP, and hitting its real limit

Picked up the Phase 2 PILZ plan from the 2026-06-01 session and actually wired it in. Got the PILZ
pipeline loaded in `move_group`, switched the controller to PTP, and rebuilt `MOVING_TO_OBJECT` to
resolve the object pose to a trusted joint config via IK before planning. Every piece of *plumbing*
now works — but the session ended on a clean architectural fork: PILZ PTP, by design, can't do the
gross free-space reach to a sensed pose, because it has no collision avoidance. Decided to checkpoint
and choose between a taught via-point and a hybrid OMPL/PILZ split next session.

## What we built
- **PILZ pipeline registered in the launch.** `gazebo_ur3e.launch.py` `planning_pipelines` now lists
  both `ompl` and `pilz_industrial_motion_planner` (config: `config/pilz_planning.yaml`, which already
  existed but was never wired in). Default pipeline kept as `ompl`; Cartesian stages bypass the
  pipeline anyway. Verified live: `ros2 param list /move_group | grep -i pilz` shows the three params.
- **Controller switched to PILZ PTP** globally (`pick_place_controller.py:56-57`):
  `pipeline_id='pilz_industrial_motion_planner'`, `planner_id='PTP'`. One default covers the three
  free-space stages (1/5/9); Cartesian stages (2/4/6) are unaffected.
- **`MOVING_TO_OBJECT` rebuilt** to: async IK (`compute_ik_async`) → poll the future with a 5 s
  timeout → `None`-guard that falls through to the existing safe-home/abort → extract the 6 arm joints
  by name → PILZ PTP to that vetted joint config (`move_to_configuration`).
- **`kinematics.yaml` budget raised** — `kinematics_solver_timeout: 0.005 → 0.05`, `attempts: 3 → 10`.
- **What now works that didn't:** PILZ loaded; IK solves for the low pose; joint extraction is correct;
  the failure path aborts cleanly and safe-homes with no crash. (`safe_height` was bumped to 0.20 as an
  experiment, then reverted to 0.05 — the value where IK solves.)

## Concepts learned
- **PILZ PTP is not a search.** It computes one deterministic straight line in joint space and
  collision-checks it. No avoidance, no rerouting. More time/attempts changes nothing. This is *why*
  it's repeatable — and why it can't get around the floor. (See gotcha #14.)
- **Why OMPL succeeded where PILZ fails on the same reach.** OMPL samples and routes around obstacles;
  it also calls IK many times with random seeds for goal sampling. A single `compute_ik` gets one seed
  and ~5 ms — hence the `NO_IK_SOLUTION` until we raised the budget. (Gotcha #15.)
- **KDL is local and seed-sensitive.** The solution sits in a "basin" near the seed. Raising the target
  15 cm moved the solution to a different basin the (low-pick-tuned) seed no longer reached → IK failed.
  Fixed seed ↔ target height is a fragile coupling. TRAC-IK (Phase 6) is the proper answer.
- **`JointState` is a name↔position map over the whole robot.** `compute_ik` returns all joints
  (arm + gripper); index by name for the subset you want, never slice `[:6]`. (Gotcha #17.)
- **pymoveit2 sync helpers spin the node.** `compute_ik()` / `wait_until_executed()` call
  `rclpy.spin_once(self._node)`, which races a `MultiThreadedExecutor` and crashes
  (`AttributeError: __enter__`). Use the `*_async` form + poll. (Gotcha #16.)

## Code & commands
```python
# Register both pipelines (gazebo_ur3e.launch.py)
planning_pipelines = {
    'planning_pipelines': ['ompl', 'pilz_industrial_motion_planner'],
    'default_planning_pipeline': 'ompl',
    'ompl': load_yaml(sim_pkg, 'config/ompl_planning.yaml'),
    'pilz_industrial_motion_planner': load_yaml(sim_pkg, 'config/pilz_planning.yaml'),
}

# Resolve pose -> trusted joint config, then PTP to it (MOVING_TO_OBJECT)
ik_future = self.moveit2.compute_ik_async(
    position=[obj_pos.x, obj_pos.y, obj_safe_z],
    quat_xyzw=[obj_ori.x, obj_ori.y, obj_ori.z, obj_ori.w],
    start_joint_state=[0.1, -0.8, 0.75, -1.4, -1.6, 0.0],   # seed near pick basin
)
start_time_ik = time.time()
while not ik_future.done():
    if time.time() - start_time_ik > 5.0:
        break
    time.sleep(0.05)
target_config = self.moveit2.get_compute_ik_result(ik_future)
# extract group joints by name (JointState carries ALL robot joints)
name_to_pos = dict(zip(target_config.name, target_config.position))
arm_positions = [name_to_pos[j] for j in self.moveit2.joint_names]
```
```bash
# confirm PILZ loaded
ros2 param list /move_group | grep -i pilz
# rebuild after config/launch/controller edits, then relaunch + run
colcon build --packages-select robotics_vision_sim && source install/setup.bash
ros2 launch robotics_vision_sim gazebo_ur3e.launch.py
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"
```

## Design decisions & rationale
- **Resolve pose → joint config in the controller, then PTP to the config** (rather than PTP to a
  pose). PTP to a pose lets PILZ pick its own IK solution — often wrist-flipped — whose straight-line
  interpolation self-collides. Computing IK ourselves with a chosen seed controls which solution we
  hand to PTP. Tradeoff: it couples the seed to the target (gotcha #15).
- **Global PILZ default, not per-stage.** Cartesian stages bypass the pipeline, so one default cleanly
  covers stages 1/5/9 with no per-block setting.
- **Raised the KDL budget instead of switching solvers (yet).** Direct fix first; it resolved the
  low-pose `NO_IK_SOLUTION`. TRAC-IK stays the proper Phase 6 fix and this is now concrete evidence for it.
- **Checkpointed at the fork instead of tweaking knob #4.** Low target → IK ok but PTP path dips through
  the floor; high target → IK fails. Bouncing between coupled failure modes is the signal to stop and
  pick an architecture. Open decision for next session:
  - **Via point (taught, no IK):** PTP home → fixed high "ready" config (verified clear) → short
    Cartesian descent to the box. Shrinks the adaptive part; gross move stays deterministic. Highest
    portfolio value (shows *why* industrial cells teach waypoints).
  - **Hybrid:** OMPL for the gross adaptive reach (it avoids the floor), PILZ PTP reserved for `HOMING`
    and taught-config moves. Honest that the reach isn't deterministic.
- **RViz still skipped** (gotcha #13) — motion judged in Gazebo.
