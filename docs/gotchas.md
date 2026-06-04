# Gotchas & Lessons Learned

Hard-won rules from debugging this project. **Read before debugging; append after fixing a bug.**
Each entry leads with the rule, then the why. Append new entries at the bottom — never overwrite.

---

### 1 — Edit `src/`, never `install/`; the installed copy is what runs
*2026-03-11*

The project has a root workspace and a nested `ros2_ws`. Editing/building in the wrong one means
the installed file under `ros2_ws/install/` (what actually executes) never updates — code changes
have zero effect.

- Confirm the active workspace: `echo $AMENT_PREFIX_PATH | tr ':' '\n' | head -3`
- Edit only under `ros2_ws/src/`; build from `ros2_ws` with `colcon build --packages-select <pkg> && source install/setup.bash`
- When a change has no effect, grep the installed file to confirm it matches your edit.

**Principle:** when runtime behaviour ignores a code change, verify the executed file matches the edited file. The gap is a `colcon build` from the correct root.

---

### 2 — Read actual EE orientation via FK before any Cartesian move
*2026-03-11*

The Cartesian planner interpolates position *and* orientation at every ~2.5 mm step. If the arm
arrives at pre-grasp in a slightly different orientation than the hardcoded target, IK must
correct orientation at every step and fails after ~10%. It's an orientation mismatch, not a
position or joint-limit problem.

- After a free-space move, call `compute_fk` to get the real EE pose.
- Use that FK orientation as the target for the Cartesian stage → descent becomes pure translation.
- Pattern: `move_to_configuration → compute_fk → Cartesian move using fk_pose`.

**Principle:** RRTConnect finds *any* valid IK branch, not the orientation you asked for. Always read the post-move pose before planning Cartesian motion from it.

---

### 3 — Exhaust the direct fix before pivoting
*2026-03-15*

The instinct to jump to an alternative (SDF instead of fixing URDF parenting; inline path instead
of diagnosing `GAZEBO_MODEL_PATH`) avoids the problem rather than solving it.

- Sequence: (1) diagnose *why* it fails, (2) try the natural fix, (3) try one alternative, (4) only then change approach.
- Ask: genuine technical limit, or just config friction?
- If pivoting, state the tradeoff and log the proper fix to `docs/backlog.md`.

**Principle:** a workaround that creates two sources of truth or hardcoded values is often worse than the original bug.

---

### 4 — Gazebo hangs silently on unresolved `model://` URIs
*2026-03-15*

Gazebo loads worlds synchronously. An unresolvable `model://` (bad `GAZEBO_MODEL_PATH`, missing
model dir, or uncached `ground_plane`/`sun`) makes it hang trying to fetch from the internet;
`/spawn_entity` never comes up and spawn nodes time out with "Service unavailable".

- Cache `ground_plane` and `sun` in `~/.gazebo/models`; set `GAZEBO_MODEL_DATABASE_URI=""` to disable internet fetch.
- Pass `GAZEBO_MODEL_PATH` via `os.environ[]` at the **top of the launch file** (before `generate_launch_description`) — `SetEnvironmentVariable` does not propagate to `IncludeLaunchDescription` children.
- Diagnose by running `gzserver --verbose` directly to see the real failure point.

**Principle:** Gazebo startup failures are silent. When `/spawn_entity` hangs, run `gzserver --verbose` rather than debugging the launch chain.

---

### 5 — Stage by path; never `git add -A`
*2026-03-15*

`git add -A` from the repo root stages everything, including `build/ install/ log/` — once
committed 92 files of build artifacts.

- Use `git add src/` explicitly.
- Ensure `.gitignore` has `build/`, `install/`, `log/` before the first commit.
- Check `git status` before committing.

**Principle:** `git add -A` ≠ `git add .`. In a ROS2 workspace, always stage by explicit path.

---

### 6 — Verify the OpenCV ArUco API for your version
*2026-03-15*

OpenCV's ArUco API changed across versions. On 4.5.4, `generateImageMarker` doesn't exist (use
`drawMarker`), and `detectMarkers` needs `parameters=` as a keyword arg or you get a cryptic
`Can't parse 'corners'` error.

- Check `cv2.__version__` first; use `drawMarker` for < 4.7.
- Always pass ArUco args as keywords.
- On `Bad argument / Overload resolution failed`, check keyword-vs-positional and arg order.

**Principle:** verify OpenCV version compatibility before copying ArUco code; keyword args are the safe default.

---

### 7 — rclpy action clients have no synchronous `send_goal()`
*2026-03-17*

`send_goal()` does not exist in rclpy. Only `send_goal_async()` (returns a future). Calling the
non-existent method returned a `PickPlace_GetResult_Response`, causing
`AttributeError: ... has no attribute 'accepted'`.

- Goal: `future = client.send_goal_async(goal)` → `spin_until_future_complete(self, future)` → `goal_handle = future.result()`
- Result: `result_future = goal_handle.get_result_async()` → `spin_until_future_complete(self, result_future)` → `result = result_future.result().result`

**Principle:** action clients are fully async — every interaction needs two futures. Use `spin_until_future_complete` inside a `MultiThreadedExecutor` callback to wait without blocking the executor.

---

### 8 — rclpy uses `get_result_async()`, not `get_result_future()`
*2026-03-17*

`ClientGoalHandle.get_result_future()` does not exist; the correct method is `get_result_async()`.
`result_future.result()` returns a `GetResult_Response` wrapper — `.result` on that gives the
actual Result message.

**Principle:** don't trust rclpy method names from memory. Check the source:
`python3 -c "from rclpy.action.client import ClientGoalHandle; help(ClientGoalHandle)"`.

---

### 9 — `kinematics.yaml` group name must exactly match the SRDF planning group
*migrated from project memory*

The IK solver won't register if the group name in `kinematics.yaml` doesn't match the planning
group defined in the SRDF. For this project the correct name is `ur_manipulator`, **not**
`ur3e_arm`. A mismatch produces a silently unregistered solver — MoveIt2 can't plan, with no
obvious error pointing at the YAML.

- Confirm the SRDF planning group name, then use that exact string as the top-level key in `kinematics.yaml`.

**Principle:** MoveIt config files cross-reference by exact string. When IK silently fails to load, check name agreement between SRDF and `kinematics.yaml` before anything else.

---

### 10 — Pin `gazebo_ros2_control` to 0.4.6 for large URDFs
*migrated from project memory*

`gazebo_ros2_control` above 0.4.6 fails when loading large URDFs (roughly >15 KB), which the
UR3e + Robotiq description exceeds. The failure is at controller-plugin load, not in the URDF
itself.

- Pin to 0.4.6: `git reset --hard 9a3736c` in the `gazebo_ros2_control` source, then rebuild.
- This was documented in IFRA-Cranfield's own `Installation.md` — see rule 11.

**Principle:** large combined descriptions hit version-specific limits in the Gazebo control bridge. Pin the known-good version rather than fighting the symptom.

---

### 11 — Read the reference repo's own docs before debugging from scratch
*migrated from project memory*

The URDF-size crash (rule 10) was already documented in IFRA-Cranfield's `Installation.md`. Hours
of from-scratch debugging would have been avoided by reading it first.

- When using any reference/third-party repo, read its `Installation.md` and `README.md` fully before debugging integration failures.

**Principle:** known issues and their workarounds are usually already written down by the people who hit them first. Read the reference docs before treating a failure as novel.

---

### 12 — Camera-pointing-down quaternion is `x=1.0, w=0.0` (180° about X)
*migrated from project memory*

For a camera looking straight down, the correct orientation quaternion is `rotation.x = 1.0,
w = 0.0` (a 180° rotation about X). The plausible-looking `[0, 0.707, 0, 0.707]` is wrong — it
maps the camera's Z axis to world +X, pointing the camera sideways, which silently corrupts every
pose estimate downstream.

- Verify camera frame orientation in RViz (TF display) before trusting `pose_estimation_node` output.

**Principle:** a wrong camera extrinsic produces plausible-but-wrong poses, not an error. Validate the camera TF visually before debugging the perception math.

---

### 13 — `ur_moveit_config` RViz spams errors; it doesn't know the Robotiq gripper
*2026-06-01*

Launching RViz via `ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur3e launch_rviz:=true`
floods the console with errors, because that stock UR MoveIt config describes only the arm — it has
no knowledge of the Robotiq 2F-85 gripper this project adds. RViz is therefore **skipped**; motion
quality is judged by watching the arm move directly in Gazebo.

- Don't reach for the stock `ur_moveit_config` RViz to debug motion — it's not gripper-aware here.
- If interactive/visual planning is ever needed, build a MoveIt config that includes the combined
  UR3e + Robotiq 2F-85 description (out of scope for now — see `docs/backlog.md`).

**Principle:** a stock vendor MoveIt config matches the vendor's robot, not your modified one. Adding an
end-effector means the planning/visualization config must know about it too, or it errors on the missing links.

---

### 14 — PILZ PTP has no collision avoidance; fix the geometry, not the compute
*2026-06-03*

PILZ PTP is **not a search** — it computes one deterministic straight line in joint space from
start config to goal config, then collision-checks it. If that straight line passes through the
floor or a self-collision, `move_group` rejects it ("Computed path is not valid. Invalid states at
index locations …"). Observed: a PTP reach from home to a low pick config swung the forearm/gripper
through `ground_plane` at the *mid-path* waypoints (indices 33–67 of 80).

- Giving PILZ more time or attempts buys **nothing** — it re-derives the identical line. (Contrast KDL
  IK, rule 15, which *is* iterative and benefits from more time.)
- OMPL planned the same reach fine for months because it *samples and routes around* obstacles.
- Fix is **geometric**: change the path's endpoints/waypoints (a taught via-point that's verified
  clear), or use a planner with avoidance (OMPL) for the gross reach. You cannot fix a mid-path
  collision by moving an endpoint.

**Principle:** PILZ PTP is for deterministic moves between *known, verified-clear* configs (home, via
points). It is the wrong tool for an adaptive reach to a sensed pose that must avoid obstacles —
that needs a sampling planner or taught waypoints.

---

### 15 — Single-shot KDL IK is seed- and budget-sensitive
*2026-06-03*

A direct `compute_ik` call uses KDL — a *local, iterative* solver — once, with the tiny default
budget (`kinematics_solver_timeout: 0.005`, `attempts: 3`). It returned `NO_IK_SOLUTION` for a pose
that `move_to_pose`+OMPL reached easily, because OMPL's goal sampler calls IK *many* times with
random seeds while a single `compute_ik` gets one seed and ~5 ms.

- Raising `kinematics_solver_timeout` to `0.05` and `attempts` to `10` in `kinematics.yaml` fixed the
  low-pose case (config installs to share dir → `colcon build` + relaunch to take effect).
- The seed (`start_joint_state`) must be in the **same IK basin** as the target. A seed tuned for a
  low pick config caused `NO_IK_SOLUTION` when the target was raised 15 cm — the solution moved to a
  different, more-upright basin the seed no longer pointed at. Fixed seed ↔ target height is a
  fragile coupling.
- Real fix is on the roadmap: replace KDL with TRAC-IK (Phase 6) — far less seed-sensitive.

**Principle:** a single `compute_ik` is not the robust IK that a pose-goal planner gives you for free.
With KDL, give it budget *and* a seed near the expected solution — or switch to TRAC-IK.

---

### 16 — pymoveit2 sync calls spin the node → crash inside a MultiThreadedExecutor
*2026-06-03*

`compute_ik()` (sync) and `wait_until_executed()` call `rclpy.spin_once(self._node)` internally. The
controller already spins that node in a `MultiThreadedExecutor`, so two things spin one node → a
context race that throws `AttributeError: __enter__` and kills the node. It only surfaced once a
planning *failure* exercised the path that calls these.

- Use the **async** API and poll the future yourself, letting the executor's threads service it:
  `fut = moveit2.compute_ik_async(...)` → `while not fut.done(): sleep + timeout` → `get_compute_ik_result(fut)`.
- Never call a library helper that spins the node from inside a callback already driven by your executor.

**Principle:** in a `MultiThreadedExecutor` app, the executor owns spinning. Any API that spins the node
itself will race — prefer its `*_async` form and poll.

---

### 17 — `compute_ik` returns a full-robot `JointState`; extract group joints by name
*2026-06-03*

The `JointState` from `compute_ik` carries **all** robot joints (arm + Robotiq gripper), not just the
planning group. Handing its `.position` straight to `move_to_configuration` gave `IndexError: list
index out of range` in `create_joint_constraints` (the position list was longer than the 6 arm
joint names).

- `JointState.name[]` and `.position[]` are parallel arrays; build `dict(zip(name, position))` and
  pull out the group joints in order: `[name_to_pos[j] for j in moveit2.joint_names]`.
- Do **not** slice `[:6]` — IK's joint order is not guaranteed to match the group's.

**Principle:** a `JointState` is a name↔position map over the whole robot. Always index it by joint
name for the subset you want, never by position.

---

### 18 — Spinning the node from inside its own executor corrupts `node.executor`; lazy clients then hang
*2026-06-05* (deepens #16)

`rclpy.spin_until_future_complete(self, fut)` and `rclpy.spin_once(self)` (no `executor=`) grab the
**global `SingleThreadedExecutor`**, call `add_node(self)` — which **reassigns `node.executor` to it**
— spin, then `remove_node`, which **never restores the pointer**. After that, `node.executor` dangles
at the idle global executor. pymoveit2's `wait_until_executed()` does this via `spin_once` on *every*
motion, so the corruption happens early (stage 1), silently.

- **Symptom:** a service future created *later* (our stage-5 `compute_ik`) **never completes** — 5 s
  `future is not done`, not a crash. Its wait-set registration (`node.executor.wake()`) goes to the
  dead executor, so the live `MultiThreadedExecutor` never watches that mailbox.
- **Dormant:** only the **next lazily-created client** dies. Clients made in `__init__` (gripper,
  attach, detach) survive — they were registered before any spin. Scene of crime ≠ scene of body.
- **Sync survives, async-poll dies:** sync `compute_fk` / `compute_ik` `spin_once` the node *themselves*
  to drive their own future, so they don't depend on the live executor. `*_async` + `while not
  fut.done(): sleep` does.

**Fix:** never spin the node from inside an executor-driven callback. Poll futures instead
(`_wait_for_future`), create clients eagerly, and where a lib only offers a node-spinning sync wait
(`wait_until_executed`), prefer its non-spinning form (poll `query_state()`). Stage-5 IK was fixed by
switching to **sync `compute_ik`** (immune, self-spins) — #16's blanket "no sync compute_ik" only holds
under *concurrent* spinning, which a serial single callback doesn't have. See [[ROS2 Executors, Threads and Spinning]].

---

### 19 — `colcon build` in the repo root poisons paths and silently drops the Gazebo camera
*2026-06-05*

Running `colcon build` from the **repo root** (not `ros2_ws/`) creates a stray `build/ install/ log/`
in the root (and they're **not** gitignored there — `git add -A` would commit them, see #5). Worse: if
you then `source` the **root** `install/setup.bash`, it prepends to `AMENT_PREFIX_PATH`, so
`get_package_share_directory('robotics_vision_sim')` resolves to that **incomplete** install. The launch
sets `GAZEBO_MODEL_PATH` from there → camera `model://` URIs don't resolve → **Gazebo silently drops the
camera** (no `/camera/image_raw`, no ArUco detections, no error). Tell: the build warns
`AMENT_PREFIX_PATH ... /install/... doesn't exist` — your shell is poisoned.

**Fix:** always `colcon build` **and** `source` from `ros2_ws/`. After an accidental root build, delete
the stray `build/ install/ log/` and open a **fresh terminal** to clear the poisoned env. See
[[ROS2 Workspaces and Sourcing]].

---

### 20 — PILZ PTP self-collides when KDL hands it a contorted IK config
*2026-06-05*

A `compute_ik`→`move_to_configuration` PTP can be rejected as a **self-collision** (e.g.
`robotiq_85_left_finger_link` ↔ `upper_arm_link`) even when the move is geometrically trivial. Our
object→target was a pure **~90° base rotation** (same radius 0.447 m, same height), so the ideal config
is "start joints, `shoulder_pan` +90°, rest unchanged". But KDL (local solver, cold seed) returned a
far-basin config (`[IK] delta` = base +5.3, wrist_1 −7.1 rad). PTP **linearly interpolates** every joint,
so that contortion sweeps the gripper through the arm across most of the path (indices 14–63/78).

- More PTP time/attempts changes nothing (#14). The lever is the **IK solution**, set by the seed.
- **Fix:** seed KDL into the right basin — pass `start_joint_state` = current joints with `shoulder_pan`
  pre-advanced by the pick→place Cartesian angle. Verify with a `[IK] delta` log: it should collapse to
  small, non-colliding values. If not, use a taught via-point. TRAC-IK (Phase 6) reduces this fragility.
  See [[Inverse Kinematics]], gotcha #15.

---

### TF2 note — prefer the single-call transform API

Not a bug, but a standing convention: use `tf_buffer.transform(msg, 'base_link')` as one call
rather than manual `lookup_transform` + `do_transform_pose_stamped`. Fewer moving parts, fewer
frame/timestamp mismatches.
