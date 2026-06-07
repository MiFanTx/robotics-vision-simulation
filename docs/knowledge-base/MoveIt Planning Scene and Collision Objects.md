---
tags: [moveit2, planning-scene, collision, grasping]
---

# MoveIt Planning Scene and Collision Objects

## What it is
The **planning scene** is MoveIt's *world model for collision checking* — the only thing the
planner (OMPL, PILZ, …) looks at when deciding whether a path is valid. It contains: the robot
itself, any **attached** objects (things being carried), and any **world `CollisionObject`s** you
explicitly publish. That's it.

## Why it exists (the one big idea)
**The planning scene is NOT the physics simulation.** They are two separate worlds:

- **Gazebo** = the *physics* world. Objects have mass, get knocked around, fall.
- **MoveIt planning scene** = the *planner's belief*. It only knows what's been told to it.

MoveIt cannot see Gazebo, and Gazebo cannot see MoveIt. **You are the bridge.** If a Gazebo object
isn't mirrored into the planning scene, the planner is blind to it and will happily route straight
through it. "OMPL has collision avoidance" only means "OMPL avoids what's *on its map*." Analogy: a
driver avoids every obstacle *drawn on the map* — an undrawn pothole gets driven through.

## How it works
- **Add a world obstacle:** `add_collision_box(id, size, position, quat_xyzw, frame_id)`. It
  **publishes** to a topic and returns immediately — `move_group` (a separate process) needs a short
  settle (~0.2 s) to apply it before you plan, or you plan against the old scene. (The `publish()`
  needs no spin on your side; the delay is the *other* node applying it.)
- **Attach to the robot:** `attach_collision_object(id, link_name, touch_links=[...])`. The object
  becomes part of the robot, riding on `link_name`. `touch_links` lists the links *allowed* to
  contact it without counting as a collision — for a held object that's the **whole gripper link
  set**, not just the fingertips. (`touch_links` takes **link** names, not joint names.)
- **Remove / detach:** `detach_collision_object(id)` (back to a world object) and
  `remove_collision_object(id)` (gone entirely).

## The lifecycle (get this wrong → trade one collision for another)
A grasped object must **change role** as it changes hands:

1. **Add** as a world obstacle *before the reach* → the planner routes around it.
2. **Attach** to the gripper *at grasp* → two reasons: (a) the closed fingers touching it stop
   counting as collisions (via `touch_links`), and (b) when you LIFT, the planner knows the object
   rose *with* the arm — otherwise it still thinks a phantom object sits on the ground where the
   gripper now is, and refuses to plan.
3. **Detach + remove** *at place* → no longer part of the robot, gone from the scene.

Three "attach"-like mechanisms exist and must not be confused:
- **`GripperCommand`** moves the real fingers (actuator/controller).
- **LinkAttacher** (`/ATTACHLINK`) welds the object to the gripper in **Gazebo physics** (sim grasp
  aid — Gazebo Classic friction is too weak to hold).
- **`attach_collision_object`** updates **MoveIt's belief** only (no physics).
Keep physics (LinkAttacher) and the map (`attach_collision_object`) in sync *by hand* — update both
together at grasp and at place.

## Vision vs. geometry for the object's pose
ArUco's pose is good in-plane (x, y, yaw) but **noisy along the camera optical axis (z)**. For a
known object on a known surface, take **x,y from vision** and **derive z from geometry** (surface
height + box size). Not cheating — it's using a reliable prior over a noisy sensor axis, which is
exactly the judgment a vision system should make. Isolate it behind a seam so a future markerless
6-DOF estimator can supply a *perceived* z instead.

## How it showed up in my project
The OMPL reach knocked the box aside — it was in Gazebo but never in the planning scene (gotcha #22).
Added the box → attached at GRASPING → detached+removed at PLACING. `touch_links` with only the
fingertips left `robotiq_85_base_link ↔ aruco_box` flagged; widening to the full gripper link set
fixed it. The place also drove the held box into the floor until we derived the place z from the
grasp geometry instead of the noisy target z.

Related: [[MoveIt2 and Planning Pipelines]] · [[Sampling-Based Motion Planning]] ·
[[ArUco Marker Detection]] · [[Inverse Kinematics]] · gotcha #22.
