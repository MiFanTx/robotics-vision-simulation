from setuptools import setup
import os
from glob import glob

package_name = 'robotics_vision_sim'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
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
        ],
    },
)
