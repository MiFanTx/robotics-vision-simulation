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
    xacro_file = os.path.join(get_package_share_directory('robotics_vision_sim'), 'urdf', 'ur3e_robotiq_2f85.urdf.xacro')
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc, mappings={
        'name': 'ur3e',
        'ur_type': 'ur3e',
        'sim_gazebo': 'true',
        'simulation_controllers': os.path.join(
            get_package_share_directory('robotics_vision_sim'),
            'config',
            'ur_controllers.yaml'
        )
    })
    robot_description = {'robot_description': doc.toxml()}

    # Camera SDF
    camera_sdf_path = os.path.join(
        get_package_share_directory('robotics_vision_sim'),
        'urdf',
        'camera.sdf'
    )

    spawn_camera = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-file', camera_sdf_path,'-entity', 'camera'],
        output='screen'
    )

    # Camera tf broadcaster
    camera_tf_broadcaster = Node(
        package='robotics_vision_sim',
        executable='camera_tf_broadcaster',
        output='screen'
    )

    pick_place_controller = Node(
        package='robotics_vision_sim',
        executable='pick_place_controller',
        output='screen'
    )

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

    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
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

    delayed_gripper_controller = TimerAction(
        period=5.0,
        actions=[gripper_controller_spawner]
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_entity,
        spawn_camera,
        camera_tf_broadcaster,
        pick_place_controller,
        delayed_joint_state_broadcaster,
        delayed_joint_trajectory_controller,
        delayed_gripper_controller
    ])
