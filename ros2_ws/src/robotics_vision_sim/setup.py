from setuptools import setup
import os
from glob import glob

package_name = 'robotics_vision_sim'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name, package_name + '.nodes'],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml') + glob('config/*.srdf')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'urdf', 'robotiq_2f85'), glob('urdf/robotiq_2f85/*')),
        (os.path.join('share', package_name, 'meshes', 'robotiq_2f85'), glob('meshes/robotiq_2f85/*.stl')),
        (os.path.join('share', package_name, 'meshes', 'robotiq_2f85', 'visual'), glob('meshes/robotiq_2f85/visual/*')),
        (os.path.join('share', package_name, 'meshes', 'robotiq_2f85', 'collision'), glob('meshes/robotiq_2f85/collision/*')),
        (os.path.join('share', package_name, 'models', 'aruco_box'), glob('models/aruco_box/*.*')),
        (os.path.join('share', package_name, 'models', 'aruco_box', 'materials', 'textures'), glob('models/aruco_box/materials/textures/*')),
        (os.path.join('share', package_name, 'models', 'aruco_box', 'materials', 'scripts'), glob('models/aruco_box/materials/scripts/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Yide Fan',
    maintainer_email='mifantx@hotmail.com',
    description='Robotics vision simulation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_tf_broadcaster = robotics_vision_sim.nodes.camera_tf_broadcaster:main',
            'pick_place_controller = robotics_vision_sim.nodes.pick_place_controller:main',
            'vision_pipeline_node = robotics_vision_sim.nodes.vision_pipeline_node:main',
            'pose_estimation_node = robotics_vision_sim.nodes.pose_estimation_node:main',
            'task_manager_node = robotics_vision_sim.nodes.task_manager_node:main',
        ],
    },
)
