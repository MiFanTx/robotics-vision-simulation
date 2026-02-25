import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/yide/Workspace/robotics-vision-simulation/install/robotics_vision_sim'
