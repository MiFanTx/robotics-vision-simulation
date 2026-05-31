# Daily Workflow

How to start work at home or remotely. System reference is in `system-setup.md`.

## Start-up (one command)

A `~/start_dev.sh` script (aliased to `dev`) does the daily setup:

```bash
cd ~/Workspace/robotics-vision-simulation
source venv/bin/activate
source /opt/ros/humble/setup.bash
[ -f ros2_ws/install/setup.bash ] && source ros2_ws/install/setup.bash
```

Then a quick health check: `python3 -c "import torch; print(torch.cuda.is_available())"` and `ros2 topic list`.

## Remote (from the Surface)

1. Confirm Tailscale is connected (and Clash bypasses `100.64.0.0/10`).
2. **Coding:** VS Code → Remote-SSH → `ubuntu-desktop`, open `/home/yide/Workspace/robotics-vision-simulation`, then `dev`.
3. **GUI (Gazebo/RViz):** NoMachine → Tailscale IP → terminal → `dev`.

## Build / run

```bash
cd ~/Workspace/robotics-vision-simulation/ros2_ws
colcon build --packages-select <pkg>        # or just: colcon build
source install/setup.bash
ros2 launch robotics_vision_sim <launch_file>   # TODO: fill exact launch file
```

Run one pick-and-place:

```bash
ros2 action send_goal --feedback /run_task robotics_vision_sim_msgs/action/RunTask \
  "{object_id: 'aruco_box', target_id: 'default'}"
```

## Git (stage by path — see gotcha #5)

```bash
git add src/        # never git add -A
git status
git commit -m "..."
git push
```

## Quick fixes

- **`ros2: command not found`** → `source /opt/ros/humble/setup.bash`
- **Python module missing** → activate venv; `which python3` should point inside `venv/`
- **Code change has no effect** → you're editing/building the wrong workspace (gotcha #1)
- **Gazebo hangs on launch** → unresolved `model://` URI (gotcha #4); run `gzserver --verbose`
- **Can't connect remotely** → check `tailscale status` and the Clash bypass rule

## Useful aliases

`proj` (cd to project) · `dev` (setup) · `ws-build` / `ws-clean` (build/clean workspace) ·
`gpu` (nvidia-smi) · `myip` (local + Tailscale IPs).
