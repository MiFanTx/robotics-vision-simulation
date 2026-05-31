# 2026-06-01 — Re-orienting + diagnosing free-space motion (RRTConnect → PILZ)

Returning after a break, re-oriented on the project and confirmed the pick-and-place pipeline
still runs end-to-end (all 9 stages, task completes, no failures). Narrowed the open Phase 2
"motion quality" problem to a single, well-understood cause: the **free-space moves use
RRTConnect and take inefficient, non-repeatable paths**. Decided to fix them with the **PILZ
Industrial Motion Planner (PTP)**, pulled forward from Phase 6. No code changed yet — this was a
diagnosis-and-decision session.

## What we built
- Nothing new in code. Verified existing behaviour and updated docs:
  - Confirmed the launch command and recorded it (filled the `<launch_file>` TODO in `AGENTS.md`
    and `docs/workflow.md`): `ros2 launch robotics_vision_sim gazebo_ur3e.launch.py`.
  - Ran a full end-to-end `RunTask` action and watched all 9 stages complete in Gazebo.
  - Used `rqt_image_view` on `/camera/image_raw` to confirm the camera sees the box + marker.
  - Marked the Cartesian-straight-line and pre-grasp-config items **done** in `docs/roadmap.md`;
    added the PILZ free-space item as NEXT.

## Concepts learned
- **Why the camera log said `Detected: none, Rejected: 2`.** `cv2.aruco.detectMarkers` runs two
  stages: (1) find quad-shaped *candidates*, (2) decode each candidate's bit grid against the
  dictionary. `rejected` = candidates that passed shape but failed decode — correctly discarded
  noise (box edges, shadows). Only `Detected` matters; the controller acts on marker id 0.
- **Why RRTConnect produces ugly paths.** It's a *sampling-based* planner: it grows random trees
  from start and goal in joint space and stops at the **first** collision-free connection. So it's
  probabilistically complete but **not optimal**, and gives a different path each run. More
  planning time buys nothing — it already quit at first contact.
- **RRT vs RRT\*.** RRT grows a random tree toward sampled points. RRT\* adds **rewiring**: each new
  node triggers a check of whether nearby nodes are cheaper to reach *through* it, so paths keep
  improving with time. That's why "plan longer → shorter path" works for RRT\* but not RRTConnect.
- **PILZ PTP.** Not sampling at all — deterministic point-to-point, joint-interpolated with a
  velocity profile (like a CNC/elevator move). Same command → identical motion every time.
  Command types: **PTP** (free-space), **LIN** (straight Cartesian), **CIRC** (arc). Industrial
  standard because factories need repeatable, predictable motion.

## Code & commands
```bash
# launch (from ros2_ws, sourced)
ros2 launch robotics_vision_sim gazebo_ur3e.launch.py

# view the detector's input
ros2 run rqt_image_view rqt_image_view        # select /camera/image_raw

# full end-to-end run
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"
```
Selecting a planner in pymoveit2 (the change planned for next session, stages 1/5/9 only):
```python
self.moveit2.pipeline_id = 'pilz_industrial_motion_planner'   # was 'ompl'
self.moveit2.planner_id  = 'PTP'                              # was 'RRTConnect'
```

## Design decisions & rationale
- **Stages split into two motion types.** Free-space reaches (1 `MOVING_TO_OBJECT`,
  5 `MOVING_TO_TARGET`, 9 `HOMING`) vs straight-line stages (2/4/6, already `cartesian=True`). Only
  the free-space ones look wrong — observed and confirmed against the code.
- **Chose PILZ PTP over the alternatives.** Considered: (A) path shortcutting on RRTConnect output —
  cheap but still random/non-optimal; (B) an optimizing planner like RRT\*/BIT\* — better but still
  non-deterministic and needs a time budget; (C) PILZ PTP — deterministic, repeatable, and the
  industry-standard answer for UR cells. Chose C for portfolio value; `docs/backlog.md` already
  flagged it. Quick-win A stays available if a fast cosmetic fix is ever needed.
- **First step before coding is to verify the PILZ pipeline is loaded in `move_group`** — you can't
  select a planner that isn't loaded. (`ros2 param list /move_group | grep -i pilz`.)
- **RViz stays skipped** (see gotcha #13): `ur_moveit_config` isn't gripper-aware, so motion quality
  is judged in Gazebo.
