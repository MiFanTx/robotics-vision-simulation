import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # Get URDF via xacro
    ur_description_path = get_package_share_directory('ur_description')
    xacro_file = os.path.join(ur_description_path, 'urdf', 'ur.urdf.xacro')
    
    robot_description_config = xacro.process_file(
        xacro_file,
        mappings={
            'name': 'ur3e',
            'ur_type': 'ur3e',
            'sim_gazebo': 'true',
            'simulation_controllers': os.path.join(
                get_package_share_directory('robotics_vision_sim'), 
                'config', 
                'ur_controllers.yaml'
            )
        }
    )
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    # Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
    )

    # Spawn Robot
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'ur3e'],
        output='screen'
    )

    # Spawn Controllers (after robot is spawned)
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    joint_trajectory_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_trajectory_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Delay controller spawning to ensure robot is loaded first
    delayed_joint_state_broadcaster = TimerAction(
        period=3.0,
        actions=[joint_state_broadcaster_spawner]
    )

    delayed_joint_trajectory_controller = TimerAction(
        period=4.0,
        actions=[joint_trajectory_controller_spawner]
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_entity,
        delayed_joint_state_broadcaster,
        delayed_joint_trajectory_controller,
    ])
