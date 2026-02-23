#!/usr/bin/env python3
"""
CUDA Compatibility Test
Checks if PyTorch CUDA version matches system CUDA installation
"""

import sys
import subprocess
import re

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{BOLD}{'='*70}{END}")
    print(f"{BLUE}{BOLD}{text.center(70)}{END}")
    print(f"{BLUE}{BOLD}{'='*70}{END}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{END}")

def print_error(text):
    print(f"{RED}✗ {text}{END}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{END}")

def print_info(text):
    print(f"  {text}")

def get_nvidia_driver_cuda():
    """Get CUDA version from nvidia-smi"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'CUDA Version:\s*(\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)
    except:
        pass
    return None

def get_nvcc_version():
    """Get CUDA toolkit version from nvcc"""
    try:
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'release (\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)
    except:
        pass
    return None

def get_pytorch_cuda():
    """Get PyTorch's CUDA version"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.version.cuda
    except:
        pass
    return None

def get_pytorch_version():
    """Get PyTorch version"""
    try:
        import torch
        return torch.__version__
    except:
        return None

def test_cuda_functionality():
    """Test if CUDA actually works with PyTorch"""
    try:
        import torch
        
        if not torch.cuda.is_available():
            return False, "CUDA not available in PyTorch"
        
        # Try to create tensor on GPU
        x = torch.rand(1000, 1000).cuda()
        y = x * 2
        z = y.cpu()
        
        # Try a more complex operation
        a = torch.rand(100, 100).cuda()
        b = torch.rand(100, 100).cuda()
        c = torch.matmul(a, b)
        
        return True, "GPU computation successful"
    except Exception as e:
        return False, str(e)

def main():
    print_header("CUDA COMPATIBILITY TEST")
    
    # Get all CUDA versions
    driver_cuda = get_nvidia_driver_cuda()
    toolkit_cuda = get_nvcc_version()
    pytorch_cuda = get_pytorch_cuda()
    pytorch_version = get_pytorch_version()
    
    print(f"{BOLD}System CUDA Information:{END}\n")
    
    # 1. NVIDIA Driver CUDA
    print(f"{BOLD}1. NVIDIA Driver (Runtime CUDA){END}")
    if driver_cuda:
        print_success(f"CUDA Runtime: {driver_cuda}")
        print_info("(This is the maximum CUDA version your driver supports)")
    else:
        print_error("Could not detect CUDA from nvidia-smi")
        print_info("Make sure NVIDIA drivers are installed")
    
    # 2. CUDA Toolkit
    print(f"\n{BOLD}2. CUDA Toolkit (Development){END}")
    if toolkit_cuda:
        print_success(f"CUDA Toolkit: {toolkit_cuda}")
        print_info("(Installed via cuda-11-8 package)")
    else:
        print_warning("nvcc not found in PATH")
        print_info("CUDA toolkit not in PATH, but PyTorch can still use CUDA runtime")
        print_info("To fix: Add to ~/.bashrc:")
        print_info("  export PATH=/usr/local/cuda-11.8/bin:$PATH")
        print_info("  export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH")
    
    # 3. PyTorch CUDA
    print(f"\n{BOLD}3. PyTorch CUDA{END}")
    if pytorch_version:
        print_success(f"PyTorch: {pytorch_version}")
        if pytorch_cuda:
            print_success(f"PyTorch CUDA: {pytorch_cuda}")
            print_info("(PyTorch was compiled with this CUDA version)")
        else:
            print_error("PyTorch not compiled with CUDA")
            print_info("Install: pip install torch --index-url https://download.pytorch.org/whl/cu118")
    else:
        print_error("PyTorch not installed")
    
    # Compatibility Analysis
    print(f"\n{BOLD}{'='*70}{END}")
    print(f"{BOLD}COMPATIBILITY ANALYSIS{END}")
    print(f"{BOLD}{'='*70}{END}\n")
    
    if not all([driver_cuda, pytorch_cuda]):
        print_error("Cannot perform full compatibility check")
        return 1
    
    driver_major = float(driver_cuda)
    pytorch_major = float(pytorch_cuda)
    toolkit_major = float(toolkit_cuda) if toolkit_cuda else None
    
    # Check 1: Driver must support PyTorch CUDA
    print(f"{BOLD}Check 1: Driver Support{END}")
    if driver_major >= pytorch_major:
        print_success(f"Driver CUDA {driver_cuda} >= PyTorch CUDA {pytorch_cuda} ✓")
        print_info("Your driver supports PyTorch's CUDA version")
    else:
        print_error(f"Driver CUDA {driver_cuda} < PyTorch CUDA {pytorch_cuda}")
        print_info("Driver too old for this PyTorch version")
    
    # Check 2: Toolkit version (less critical)
    print(f"\n{BOLD}Check 2: Toolkit Version{END}")
    if toolkit_major:
        if toolkit_major == pytorch_major:
            print_success(f"Toolkit {toolkit_cuda} matches PyTorch {pytorch_cuda} ✓")
        elif abs(toolkit_major - pytorch_major) <= 0.5:
            print_warning(f"Minor version mismatch: Toolkit {toolkit_cuda} vs PyTorch {pytorch_cuda}")
            print_info("Usually not a problem - minor versions are compatible")
        else:
            print_warning(f"Toolkit {toolkit_cuda} differs from PyTorch {pytorch_cuda}")
            print_info("This is OK - PyTorch uses its own CUDA runtime")
    else:
        print_warning("Toolkit not in PATH")
        print_info("PyTorch will use its bundled CUDA runtime")
    
    # Check 3: Functional test
    print(f"\n{BOLD}Check 3: Functional Test{END}")
    success, message = test_cuda_functionality()
    if success:
        print_success(message)
        print_info("PyTorch can successfully use your GPU!")
    else:
        print_error(f"GPU test failed: {message}")
    
    # Summary
    print(f"\n{BOLD}{'='*70}{END}")
    print(f"{BOLD}SUMMARY{END}")
    print(f"{BOLD}{'='*70}{END}\n")
    
    if success and driver_major >= pytorch_major:
        print(f"{GREEN}{BOLD}✓ CUDA SETUP IS CORRECT!{END}\n")
        print("Your system configuration:")
        print(f"  • Driver supports CUDA up to: {driver_cuda}")
        print(f"  • PyTorch uses CUDA: {pytorch_cuda}")
        if toolkit_major:
            print(f"  • Toolkit version: {toolkit_cuda}")
        print(f"\n{GREEN}Everything is working correctly!{END}")
        return 0
    else:
        print(f"{RED}{BOLD}✗ CUDA ISSUES DETECTED{END}\n")
        
        if not success:
            print("GPU computation failed. Possible causes:")
            print("  1. Driver issue - reinstall NVIDIA drivers")
            print("  2. PyTorch not properly installed")
            print("  3. GPU is being used by another process")
        
        if driver_major < pytorch_major:
            print(f"\nDriver too old:")
            print(f"  Current: {driver_cuda}")
            print(f"  Required: {pytorch_cuda}+")
            print(f"  Fix: sudo ubuntu-drivers install nvidia-driver-535")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
