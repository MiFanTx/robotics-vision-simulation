#!/usr/bin/env python3
"""Test that all components are installed correctly"""

import sys

print("=" * 70)
print("TESTING INSTALLATION")
print("=" * 70)

# Test 1: Python version
print("\n[1/8] Testing Python...")
print(f"  ✓ Python {sys.version.split()[0]}")

# Test 2: OpenCV
print("\n[2/8] Testing OpenCV...")
try:
    import cv2
    print(f"  ✓ OpenCV {cv2.__version__}")
    # Test ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    print(f"  ✓ ArUco module available")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 3: PyTorch
print("\n[3/8] Testing PyTorch...")
try:
    import torch
    print(f"  ✓ PyTorch {torch.__version__}")
    print(f"  ✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  ✓ GPU: {torch.cuda.get_device_name(0)}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 4: Scientific libraries
print("\n[4/8] Testing Scientific Stack...")
try:
    import numpy as np
    import scipy
    import matplotlib
    print(f"  ✓ NumPy {np.__version__}")
    print(f"  ✓ SciPy {scipy.__version__}")
    print(f"  ✓ Matplotlib {matplotlib.__version__}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 5: Transformers (for Depth-Anything)
print("\n[5/8] Testing Transformers...")
try:
    import transformers
    print(f"  ✓ Transformers {transformers.__version__}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 6: Open3D
print("\n[6/8] Testing Open3D...")
try:
    import open3d as o3d
    print(f"  ✓ Open3D {o3d.__version__}")
except Exception as e:
    print(f"  ⚠  Open3D not available (optional): {e}")

# Test 7: Check model weights
print("\n[7/8] Checking Model Weights...")
import os
checkpoint_dir = "checkpoints"
if os.path.exists(checkpoint_dir):
    weights = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pth')]
    if weights:
        print(f"  ✓ Found {len(weights)} model weight file(s)")
        for w in weights:
            print(f"    - {w}")
    else:
        print(f"  ⚠  No .pth files found in checkpoints/")
else:
    print(f"  ⚠  checkpoints/ directory not found")

# Test 8: Check ROS 2 (via environment variable)
print("\n[8/8] Checking ROS 2...")
ros_distro = os.environ.get('ROS_DISTRO')
if ros_distro:
    print(f"  ✓ ROS 2 {ros_distro} detected")
else:
    print(f"  ⚠  ROS 2 not sourced (run: source /opt/ros/humble/setup.bash)")

print("\n" + "=" * 70)
print("INSTALLATION TEST COMPLETE")
print("=" * 70)
