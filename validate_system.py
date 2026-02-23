#!/usr/bin/env python3
"""
Comprehensive System Validation Script
Tests all components of the robotics-vision-simulation setup
"""

import sys
import os
import subprocess
from pathlib import Path

# ANSI color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}[{text}]{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}  ✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}  ✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}  ⚠ {text}{Colors.END}")

def print_info(text):
    print(f"    {text}")

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

# Track test results
results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_python():
    """Test Python installation"""
    print_section("1/12 Testing Python Environment")
    
    # Python version
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_info(f"Python version: {version}")
    
    if sys.version_info >= (3, 10):
        print_success(f"Python {version} ✓")
        results['passed'].append("Python 3.10+")
    else:
        print_error(f"Python {version} - Requires 3.10+")
        results['failed'].append("Python version")
    
    # Virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        print_success("Virtual environment active")
        results['passed'].append("Virtual environment")
    else:
        print_warning("Not in virtual environment (run: source venv/bin/activate)")
        results['warnings'].append("Virtual environment not active")

def test_opencv():
    """Test OpenCV installation"""
    print_section("2/12 Testing OpenCV")
    
    try:
        import cv2
        version = cv2.__version__
        print_success(f"OpenCV {version}")
        results['passed'].append(f"OpenCV {version}")
        
        # Test CUDA support
        try:
            cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
            if cuda_count > 0:
                print_success(f"OpenCV CUDA support: {cuda_count} device(s)")
                results['passed'].append("OpenCV CUDA")
            else:
                print_info("OpenCV built without CUDA (CPU only)")
        except:
            print_info("OpenCV built without CUDA (CPU only)")
        
        # Test ArUco
        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            print_success("ArUco dictionary loaded")
            results['passed'].append("ArUco module")
        except Exception as e:
            print_error(f"ArUco not available: {e}")
            results['failed'].append("ArUco module")
            
    except ImportError as e:
        print_error(f"OpenCV not installed: {e}")
        results['failed'].append("OpenCV")

def test_pytorch():
    """Test PyTorch installation"""
    print_section("3/12 Testing PyTorch")
    
    try:
        import torch
        print_success(f"PyTorch {torch.__version__}")
        results['passed'].append(f"PyTorch {torch.__version__}")
        
        # CUDA availability
        if torch.cuda.is_available():
            print_success(f"CUDA available: {torch.version.cuda}")
            print_success(f"GPU: {torch.cuda.get_device_name(0)}")
            print_info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            results['passed'].append("PyTorch CUDA")
            
            # Test GPU computation
            try:
                x = torch.rand(5, 3).cuda()
                y = x * 2
                print_success("GPU computation test passed")
                results['passed'].append("GPU computation")
            except Exception as e:
                print_error(f"GPU computation failed: {e}")
                results['failed'].append("GPU computation")
        else:
            print_warning("CUDA not available - using CPU only")
            results['warnings'].append("PyTorch CPU only")
            
    except ImportError as e:
        print_error(f"PyTorch not installed: {e}")
        results['failed'].append("PyTorch")

def test_nvidia_drivers():
    """Test NVIDIA drivers"""
    print_section("4/12 Testing NVIDIA Drivers")
    
    success, output = run_command("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
    
    if success and output:
        lines = output.split('\n')
        for line in lines:
            if line.strip():
                print_success(f"GPU detected: {line}")
                results['passed'].append("NVIDIA GPU detected")
    else:
        print_error("nvidia-smi not working")
        results['failed'].append("NVIDIA drivers")
        return
    
    # Check CUDA version
    success, output = run_command("nvidia-smi | grep 'CUDA Version'")
    if success:
        print_info(output)

def test_cuda():
    """Test CUDA installation"""
    print_section("5/12 Testing CUDA Toolkit")
    
    success, output = run_command("nvcc --version")
    
    if success and output:
        # Extract version from output
        for line in output.split('\n'):
            if 'release' in line.lower():
                print_success(f"CUDA Toolkit: {line.strip()}")
                results['passed'].append("CUDA Toolkit")
                break
    else:
        print_warning("nvcc not found - CUDA toolkit may not be installed or not in PATH")
        print_info("PyTorch can still use CUDA runtime without toolkit")
        results['warnings'].append("CUDA toolkit not in PATH")

def test_scientific_stack():
    """Test scientific computing libraries"""
    print_section("6/12 Testing Scientific Stack")
    
    libraries = {
        'numpy': 'NumPy',
        'scipy': 'SciPy',
        'matplotlib': 'Matplotlib',
        'PIL': 'Pillow'
    }
    
    for module, name in libraries.items():
        try:
            lib = __import__(module)
            version = getattr(lib, '__version__', 'unknown')
            print_success(f"{name} {version}")
            results['passed'].append(f"{name}")
        except ImportError:
            print_error(f"{name} not installed")
            results['failed'].append(name)

def test_transformers():
    """Test Transformers library"""
    print_section("7/12 Testing Transformers & Deep Learning")
    
    try:
        import transformers
        print_success(f"Transformers {transformers.__version__}")
        results['passed'].append("Transformers")
    except ImportError:
        print_error("Transformers not installed")
        results['failed'].append("Transformers")
    
    try:
        import timm
        print_success(f"timm {timm.__version__}")
        results['passed'].append("timm")
    except ImportError:
        print_error("timm not installed")
        results['failed'].append("timm")

def test_depth_anything():
    """Test Depth-Anything V2 setup"""
    print_section("8/12 Testing Depth-Anything V2")
    
    # Check repository
    depth_repo = Path("depth_anything_v2")
    if depth_repo.exists() and depth_repo.is_dir():
        print_success("Depth-Anything V2 repository found")
        results['passed'].append("DA-V2 repository")
    else:
        print_error("Depth-Anything V2 repository not found")
        print_info("Expected at: depth_anything_v2/")
        results['failed'].append("DA-V2 repository")
    
    # Check model weights
    checkpoint_dir = Path("checkpoints")
    if checkpoint_dir.exists():
        weights = list(checkpoint_dir.glob("*.pth"))
        if weights:
            print_success(f"Found {len(weights)} model weight file(s):")
            for w in weights:
                size_mb = w.stat().st_size / (1024*1024)
                print_info(f"  - {w.name} ({size_mb:.1f} MB)")
            results['passed'].append(f"{len(weights)} model weights")
        else:
            print_warning("No .pth files found in checkpoints/")
            results['warnings'].append("No model weights")
    else:
        print_error("checkpoints/ directory not found")
        results['failed'].append("Checkpoints directory")

def test_ros2():
    """Test ROS 2 installation"""
    print_section("9/12 Testing ROS 2")
    
    ros_distro = os.environ.get('ROS_DISTRO')
    
    if ros_distro:
        print_success(f"ROS 2 {ros_distro} detected")
        results['passed'].append(f"ROS 2 {ros_distro}")
        
        # Test ros2 command
        success, output = run_command("ros2 --version")
        if success:
            print_info(output)
        
        # Check key packages
        packages = ['ros-humble-desktop', 'ros-humble-gazebo-ros-pkgs', 'ros-humble-moveit']
        for pkg in packages:
            success, _ = run_command(f"dpkg -l | grep {pkg}")
            if success:
                print_success(f"{pkg} installed")
            else:
                print_warning(f"{pkg} not found")
    else:
        print_warning("ROS 2 not sourced")
        print_info("Run: source /opt/ros/humble/setup.bash")
        results['warnings'].append("ROS 2 not sourced")

def test_gazebo():
    """Test Gazebo installation"""
    print_section("10/12 Testing Gazebo")
    
    success, output = run_command("gazebo --version")
    
    if success and output:
        print_success(f"Gazebo: {output.split()[0]}")
        results['passed'].append("Gazebo")
    else:
        print_warning("Gazebo not found or not in PATH")
        results['warnings'].append("Gazebo")

def test_optional_tools():
    """Test optional tools"""
    print_section("11/12 Testing Optional Tools")
    
    tools = {
        'open3d': 'Open3D (3D visualization)',
        'jupyter': 'Jupyter',
        'pytest': 'pytest',
        'black': 'black (formatter)',
        'flake8': 'flake8 (linter)'
    }
    
    for module, name in tools.items():
        try:
            lib = __import__(module)
            version = getattr(lib, '__version__', '')
            print_success(f"{name} {version}")
            results['passed'].append(name)
        except ImportError:
            print_info(f"{name} not installed (optional)")

def test_project_structure():
    """Test project structure"""
    print_section("12/12 Testing Project Structure")
    
    expected_dirs = [
        'src',
        'src/vision',
        'src/robot',
        'src/simulation',
        'config',
        'data',
        'models/checkpoints',
        'scripts',
        'tests',
        'docs'
    ]
    
    for dir_path in expected_dirs:
        path = Path(dir_path)
        if path.exists():
            print_success(f"{dir_path}/")
            results['passed'].append(f"Directory: {dir_path}")
        else:
            print_warning(f"{dir_path}/ not found")
            results['warnings'].append(f"Missing: {dir_path}")
    
    # Check essential files
    essential_files = ['requirements.txt', 'README.md', '.gitignore']
    for file in essential_files:
        if Path(file).exists():
            print_success(file)
        else:
            print_warning(f"{file} not found")

def print_summary():
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    total_tests = len(results['passed']) + len(results['failed']) + len(results['warnings'])
    
    print(f"\n{Colors.BOLD}Total Tests:{Colors.END} {total_tests}")
    print(f"{Colors.GREEN}Passed:{Colors.END} {len(results['passed'])}")
    print(f"{Colors.RED}Failed:{Colors.END} {len(results['failed'])}")
    print(f"{Colors.YELLOW}Warnings:{Colors.END} {len(results['warnings'])}")
    
    if results['failed']:
        print(f"\n{Colors.RED}{Colors.BOLD}FAILED COMPONENTS:{Colors.END}")
        for item in results['failed']:
            print(f"  {Colors.RED}✗ {item}{Colors.END}")
    
    if results['warnings']:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}WARNINGS:{Colors.END}")
        for item in results['warnings']:
            print(f"  {Colors.YELLOW}⚠ {item}{Colors.END}")
    
    # Overall status
    print(f"\n{Colors.BOLD}OVERALL STATUS:{Colors.END}")
    if not results['failed']:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ System is ready for development!{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Some components need attention{Colors.END}")
        return 1

def print_recommendations():
    """Print recommendations based on test results"""
    print_header("RECOMMENDATIONS")
    
    recommendations = []
    
    # Check for critical issues
    if "PyTorch" in results['failed']:
        recommendations.append("Install PyTorch: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    
    if "OpenCV" in results['failed']:
        recommendations.append("Install OpenCV: pip install opencv-python opencv-contrib-python")
    
    if "NVIDIA drivers" in results['failed']:
        recommendations.append("Install NVIDIA drivers: sudo ubuntu-drivers autoinstall")
    
    if "Virtual environment not active" in results['warnings']:
        recommendations.append("Activate venv: source venv/bin/activate")
    
    if "ROS 2 not sourced" in results['warnings']:
        recommendations.append("Source ROS 2: source /opt/ros/humble/setup.bash")
    
    if "No model weights" in results['warnings']:
        recommendations.append("Download Depth-Anything V2 weights from HuggingFace")
    
    if recommendations:
        print(f"{Colors.YELLOW}Action items:{Colors.END}\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print(f"{Colors.GREEN}No critical issues found!{Colors.END}")
    
    print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
    print("1. Fix any failed components above")
    print("2. Run: python3 tests/test_installation.py")
    print("3. Start developing with ROS 2!")
    print(f"\n{Colors.CYAN}Useful commands:{Colors.END}")
    print("  source venv/bin/activate              # Activate Python environment")
    print("  source /opt/ros/humble/setup.bash     # Source ROS 2")
    print("  python3 scripts/generate_test_markers.py  # Generate test data")

def main():
    """Run all tests"""
    print_header("ROBOTICS VISION SIMULATION - SYSTEM VALIDATION")
    
    print(f"{Colors.CYAN}Testing installation at: {os.getcwd()}{Colors.END}")
    print(f"{Colors.CYAN}Python executable: {sys.executable}{Colors.END}")
    
    # Run all tests
    test_python()
    test_opencv()
    test_pytorch()
    test_nvidia_drivers()
    test_cuda()
    test_scientific_stack()
    test_transformers()
    test_depth_anything()
    test_ros2()
    test_gazebo()
    test_optional_tools()
    test_project_structure()
    
    # Print summary
    exit_code = print_summary()
    print_recommendations()
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
