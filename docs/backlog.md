# Backlog — Future Improvements

Enhancements out of scope for the current implementation but worth revisiting. Append as they come up.

## Vision & perception

- **Automatic camera-robot extrinsic calibration** — camera pose vs `base_link` is hardcoded in `camera_tf_broadcaster`. Real deployment should use hand-eye calibration (`easy_handeye`, `visp_hand2eye_calibration`). `pose_estimation_node` needs zero changes — only the broadcaster source changes.
- **Detection method evaluation** — ArUco is for prototyping; compare against YOLO or FoundationPose for markerless operation on arbitrary objects.

## Motion planning

- **Proper fix for elbow joint wrapping** — RRTConnect can wind the elbow to −270°. Current workaround is a path joint constraint; proper fix is seeding IK with a preferred configuration.
- **Yaw-aware grasp orientation** — controller uses a fixed gripper-down quaternion `[0.0, 0.707, 0.0, 0.707]`. For non-square objects, decompose ArUco orientation to RPY, keep only yaw, recombine with the downward pitch.
- **Dynamic pre-grasp configuration** — currently empirically taught; compute analytically from object pose so it adapts to location.
- **TRAC-IK / Bio-IK as KDL replacement** — KDL gives inconsistent configs near workspace boundaries (wrist flips, wrapped elbow). TRAC-IK (gradient descent + random restart) is more repeatable. Configure in `kinematics.yaml` under `ur_manipulator`. Prerequisite for PILZ. *(Roadmap Phase 6.)*
- **PILZ Industrial Motion Planner** — after TRAC-IK, replace RRTConnect + `compute_cartesian_path` with PILZ PTP + LIN. Deterministic, same path every run — standard in real UR deployments. *(Roadmap Phase 6.)*
- **Trajectory smoothing (intermediate)** — OMPL post-processing (shortcutting + time-parameterisation) improves RRTConnect quality with no planner change. Quick win if TRAC-IK + PILZ proves slow. *(Roadmap Phase 6.)*
- **PILZ `cartesian_limits` config missing** — `move_group` logs `robot_description_planning.cartesian_limits.max_trans_vel is not set`. PTP ignores it (works anyway) but LIN needs it. Add a `config/pilz_cartesian_limits.yaml` (`max_trans_vel/acc/dec`, `max_rot_vel`) loaded under `robot_description_planning` in the launch.
- **Stop spamming retries on deterministic planner failures** — `_execute_motion(max_retries=5)` re-runs PILZ PTP 5× on an identical, deterministically-failing path (#14) — pure log spam. Skip retries (or retry once) when the planner is PILZ.

## ROS2 architecture (proper fixes)

- **~~Replace `wait_until_executed()` with a non-spinning wait~~ — RETRACTED 2026-06-08.** This was based on the wrong conclusion that a non-spinning poll is safe. It isn't: pymoveit2 self-spins via the *global* executor and evicts the node from the MTE, so a non-spinning poll never completes (gotcha #21). The correct model is the **opposite** — embrace self-spinning consistently (`_wait_for_future` now `spin_once`s, matching `compute_fk`/sync `compute_ik`). No further action; the bug class is closed by one consistent self-spin discipline, not by removing spins.
- **Eager client creation** — create all service/action clients (incl. pymoveit2's IK/FK) in `__init__`, never lazily inside callbacks, so a self-spin can drive them (#18, #21).
- **Physically detach on abort** — the abort path detaches the object from MoveIt's scene only, not the LinkAttacher physics weld (#22). On a real abort the box stays welded to the gripper in Gazebo. Add a guarded `DetachLink` call (no-op if nothing attached) to the recovery path.
- **Mimic-joint flick mitigation** — Robotiq fingers move asymmetrically/flick on release because Gazebo Classic + pinned `gazebo_ros2_control` v0.4.6 ignore URDF `<mimic>` joints. Proper fix is Phase 6 (mimic plugin or dual-finger transmissions). Cheap band-aid: lower grasp `max_effort` (currently 10.0) so fingers strain/snap less. Confirm root cause first: does it flick on a bare open/close with no box?
- **Generalize z-decoupling for multi-object / tables** — grasp/place z is derived from `self.surface_z` + `self.box_height` (single box on the ground). For multiple objects, make box size a per-`object_id` lookup; for non-flat placement, add `surface_z` per `TARGET_POSES` entry and use the general `place_tcp_z = grasp_z + (place_surface_z − pick_surface_z)`. Keep a `_resolve_grasp_z` seam isolated so markerless detection can later supply a *perceived* z instead of a prior.

## System & infrastructure

- **On-demand detection service** — `vision_pipeline_node` runs continuously and publishes `/vision/object_pose`. Alternative: expose detection as a service the task manager calls per pick. Tradeoff: more latency, no wasted CPU between picks.
- **Target pose detection** — place target is hardcoded; detect it (tray/bin) with the same vision pipeline.
- **Robot base position auto-detection** — `base_link → world` is a hardcoded static TF; read from config or calibrate against fiducials.
- **Proper object SDF model** — replace the basic box with realistic mass, inertia, surface properties.
- **Proximity-based grasp validation** — confirm object is within gripper volume (EE link position + joint states) before calling LinkAttacher.

## Portfolio & documentation

- **Switch from ArUco to markerless detection** — ArUco starts simple but is unimpressive on a CV portfolio; a learning-based detector shows depth.
- **Real hardware transfer** — document the sim→real delta: `camera_tf_broadcaster` → calibration loader, LinkAttacher → real gripper driver, motion-parameter tuning.
