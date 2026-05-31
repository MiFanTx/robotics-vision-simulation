# System Setup Reference

Machine, drivers, and environment for the robotics-vision-simulation project.
Owner: Yide (David) Fan · Location: `~/Workspace/robotics-vision-simulation`

## Hardware

- **Desktop (dev machine):** Lenovo Legion · NVIDIA RTX 3060 Ti (8 GB) · driver 535.288.01
- **Surface laptop:** Windows, remote-access device (user `mifan`)

## OS

- Ubuntu 22.04 LTS (Jammy) · GNOME · user `yide` · host `Yide-Ubuntu-Desktop`
- Auto-login enabled (`/etc/gdm3/custom.conf`) and sleep/suspend masked, so the machine stays remotely reachable.

## Python

- System Python 3.10; project venv at `~/Workspace/robotics-vision-simulation/venv` (`source venv/bin/activate`)
- Core: numpy, scipy, matplotlib · OpenCV 4.8.1 (CPU) + contrib (ArUco) · open3d
- DL: torch 2.10 (CUDA build), torchvision, transformers, timm
- Dev: pytest, black, flake8, jupyter
- Pinned in `requirements.txt`

> Note: the old config listed CUDA toolkit 11.8 "for PyTorch" alongside a cu12x torch build — verify
> which CUDA the installed torch actually links against (`python3 -c "import torch; print(torch.version.cuda)"`)
> and update this line once confirmed.

## ROS 2

- Humble Hawksbill (apt), `ros-humble-desktop`
- Gazebo Classic 11.10.2 via `ros-humble-gazebo-ros-pkgs`, plus `gazebo-ros2-control`
- MoveIt2 (`ros-humble-moveit`)
- Source order: `/opt/ros/humble/setup.bash` → `ros2_ws/install/setup.bash`

## Remote access

- **SSH:** port 22, key auth (Surface public key in `~/.ssh/authorized_keys`)
- **Tailscale:** IP `100.90.192.101` (snap service `tailscaled`)
- **NoMachine:** for GUI/Gazebo over Tailscale

See `workflow.md` for the day-to-day start-up and remote-connection steps.
