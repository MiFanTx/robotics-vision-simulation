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

### TF2 note — prefer the single-call transform API

Not a bug, but a standing convention: use `tf_buffer.transform(msg, 'base_link')` as one call
rather than manual `lookup_transform` + `do_transform_pose_stamped`. Fewer moving parts, fewer
frame/timestamp mismatches.
