---
tags: [ros2, motion-planning, kinematics, ik]
---

# Inverse Kinematics

## What it is
**Inverse Kinematics (IK)** answers: *given a desired end-effector pose (position + orientation),
what joint angles put the arm there?* It's the inverse of Forward Kinematics (FK: joints → pose).
For a 6-DOF arm a pose usually has **multiple** IK solutions (elbow up/down, wrist flipped), and some
poses have **none** (out of reach, or blocked).

## Why it exists
We think in Cartesian space ("gripper here, pointing down"), but a robot is commanded in **joint
space**. Anything that takes a *pose* goal — a Cartesian motion-plan request, or computing a joint
target for [[PILZ Industrial Motion Planner|PILZ PTP]] — needs IK to bridge the two.

## How it works — analytic vs numerical (KDL)
- **Analytic IK** — closed-form equations; instant, returns all solutions. Needs a solver written for
  the specific arm.
- **Numerical IK** — iterates from a **seed** guess toward a solution (Jacobian / gradient style).
  This is what MoveIt2 uses by default via the **KDL** plugin (`kdl_kinematics_plugin/KDLKinematicsPlugin`).

KDL is **local and iterative**, which has three consequences that bit me hard:
1. **Seed-sensitive.** It converges to a solution *near* its seed (`start_joint_state`). The seed must
   be in the same "basin" as the target, or it won't find anything. *Analogy: a ball rolling downhill
   finds the nearest valley — where you drop it decides which valley, or whether it reaches one at all.*
2. **Budget-limited.** It gets `kinematics_solver_timeout` and `kinematics_solver_attempts`
   (in `kinematics.yaml`). The defaults (5 ms, 3 tries) are stingy; near the workspace edge it runs out
   of budget and returns `NO_IK_SOLUTION`.
3. **Not global.** Failure means *"I didn't find one from here in time,"* not *"none exists."*

```yaml
# kinematics.yaml — give the local solver room to converge
ur_manipulator:
  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
  kinematics_solver_timeout: 0.05     # was 0.005 — 10x
  kinematics_solver_attempts: 10      # was 3 — more random restarts
```

## Why a pose-goal planner feels more robust than a single `compute_ik`
A pose-goal sent to OMPL ([[Sampling-Based Motion Planning]]) calls IK **many times with random
seeds** while sampling goal states — so it almost always finds *some* valid config. A single
`compute_ik` call gets **one seed and one tiny budget**. Same KDL underneath; wildly different
robustness. (This is why `move_to_pose` worked for months but my first explicit `compute_ik` failed.)

## Using IK from pymoveit2 (two traps)
- **Use the async form + poll.** Sync `compute_ik()` calls `rclpy.spin_once(self._node)` internally,
  which races a `MultiThreadedExecutor` (see [[ROS2 Actions]]) and crashes (`AttributeError: __enter__`).
  Instead: `fut = moveit2.compute_ik_async(...)` → poll `fut.done()` with a timeout → `get_compute_ik_result(fut)`.
- **The result is a full-robot `JointState`** (arm **+** gripper joints). `.name[]` and `.position[]`
  are parallel arrays — extract your group's joints **by name**, never slice `[:6]`:
  ```python
  name_to_pos = dict(zip(target_config.name, target_config.position))
  arm_positions = [name_to_pos[j] for j in moveit2.joint_names]
  ```

## In my project
PILZ PTP needs a *joint* goal, so `MOVING_TO_OBJECT` computes IK on the object pose, then PTPs to the
config. Hit `NO_IK_SOLUTION` on a low pick pose — fixed by raising the KDL budget (above). Then learned
the **seed↔target coupling** the hard way: a seed tuned for the low pick config made IK *fail* when I
raised the hover target 15 cm (solution moved to a different basin). The proper fix is **TRAC-IK**
(roadmap Phase 6) — combines KDL with an optimization solver, far less seed-sensitive.

## Related
[[PILZ Industrial Motion Planner]] (consumes IK joint goals) · [[MoveIt2 and Planning Pipelines]] ·
[[Sampling-Based Motion Planning]] (robust because it re-seeds IK many times) · [[ROS2 Actions]]
(the async/executor trap) · back to [[ROS Knowledge Base]]
