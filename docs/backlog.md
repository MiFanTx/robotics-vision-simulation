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

## System & infrastructure

- **On-demand detection service** — `vision_pipeline_node` runs continuously and publishes `/vision/object_pose`. Alternative: expose detection as a service the task manager calls per pick. Tradeoff: more latency, no wasted CPU between picks.
- **Target pose detection** — place target is hardcoded; detect it (tray/bin) with the same vision pipeline.
- **Robot base position auto-detection** — `base_link → world` is a hardcoded static TF; read from config or calibrate against fiducials.
- **Proper object SDF model** — replace the basic box with realistic mass, inertia, surface properties.
- **Proximity-based grasp validation** — confirm object is within gripper volume (EE link position + joint states) before calling LinkAttacher.

## Portfolio & documentation

- **Switch from ArUco to markerless detection** — ArUco starts simple but is unimpressive on a CV portfolio; a learning-based detector shows depth.
- **Real hardware transfer** — document the sim→real delta: `camera_tf_broadcaster` → calibration loader, LinkAttacher → real gripper driver, motion-parameter tuning.
