---
tags: [ros2, workspace, build]
---

# ROS2 Workspaces and Sourcing

## What it is
A ROS2 **workspace** is a directory (`ros2_ws/`) where you build your packages. `colcon build`
compiles everything under `src/` and produces an `install/` tree. **Sourcing**
(`source install/setup.bash`) is the step that makes that built code visible to ROS2 tools in the
current terminal.

## Why it exists
ROS2 layers environments as **overlays** on top of an **underlay** (the system ROS2 install at
`/opt/ros/humble`). Sourcing your workspace's `install/setup.bash` overlays *your* packages on top
of the base install, so `ros2 run` / `ros2 launch` can find your nodes, launch files, messages, and
resources. Without it, the shell only knows about the underlay — your package "doesn't exist."

## How it works
- `colcon build` → writes executables, launch files, and `package.xml`/resource markers into
  `install/`.
- `source install/setup.bash` → prepends your workspace to environment variables, most importantly
  **`AMENT_PREFIX_PATH`** (the search path ROS2 uses to discover packages).
- This is **per-terminal**: every new shell starts clean, so you re-source each time (or add it to
  `~/.bashrc`).

```bash
cd ~/Workspace/robotics-vision-simulation/ros2_ws   # the WORKSPACE root, not the repo root
colcon build --packages-select <pkg>
source install/setup.bash
# check which workspace is active:
echo $AMENT_PREFIX_PATH | tr ':' '\n' | head -3
```

## In my project
- The "I can't launch Gazebo" issue was just *not being in `ros2_ws` and not sourcing*. Launch only
  works after `cd ros2_ws && source install/setup.bash`.
- **Edit only `src/`, never `install/`** — the installed copy is what runs; if an edit has no effect,
  you forgot to `colcon build` (project gotcha #1).
- World-file changes need a rebuild too — they get *installed* into the share dir.

## Related
[[ROS2 Introspection and Debugging Tools]] · [[MoveIt2 and Planning Pipelines]] · back to [[ROS Knowledge Base]]
