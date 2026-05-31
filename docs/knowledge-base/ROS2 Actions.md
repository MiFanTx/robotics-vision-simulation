---
tags: [ros2, actions, async]
---

# ROS2 Actions

## What it is
An **action** is a ROS2 communication pattern for **long-running, goal-oriented tasks** that need
**feedback** while running and can be **canceled** — e.g. "run a full pick-and-place." It sits
alongside the other two patterns:
- **Topics** — continuous streams, fire-and-forget (e.g. camera images, joint states).
- **Services** — quick request/response, blocking (e.g. attach/detach a link).
- **Actions** — request + periodic feedback + final result, for things that take seconds/minutes.

## Why it exists
A service call would block for the whole motion with no progress and no way to abort. An action lets
a client send a goal, stream feedback (`[3/9] Lowering to object...`), and cancel mid-execution.

## How it works — the async client pattern (rclpy)
**There is no synchronous `send_goal()` in rclpy.** Every interaction returns a *future*:
```python
# 1. send the goal
goal_future = client.send_goal_async(goal, feedback_callback=cb)
rclpy.spin_until_future_complete(self, goal_future)
goal_handle = goal_future.result()          # accepted/rejected handle

# 2. wait for the result
result_future = goal_handle.get_result_async()   # NOT get_result_future()
rclpy.spin_until_future_complete(self, result_future)
result = result_future.result().result            # .result twice: unwrap the response
```
Run this inside a `MultiThreadedExecutor` so `spin_until_future_complete` can wait without
deadlocking the executor. Don't trust rclpy method names from memory — `help()` the class.

## In my project
- `RunTask` action drives the whole pipeline; `task_manager_node` is the server, with a **staleness
  check** on the vision pose before accepting.
- The `pick_place_controller` runs a **9-stage state machine** and publishes per-stage feedback.
- Node pattern: `ReentrantCallbackGroup` (separate server/client groups) + `MultiThreadedExecutor`.

```bash
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"
```

## Related
[[ArUco Marker Detection]] (supplies the pose) · [[ROS2 Introspection and Debugging Tools]] · back to [[ROS Knowledge Base]]
