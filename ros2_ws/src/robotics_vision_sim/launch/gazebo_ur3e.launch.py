import os
import xacro
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def load_file(package_path, file_path):
    absolute_path = os.path.join(package_path, file_path)
    return open(absolute_path).read()


def load_yaml(package_path, file_path):
    absolute_path = os.path.join(package_path, file_path)
    return yaml.safe_load(open(absolute_path))

os.environ['GAZEBO_MODEL_PATH'] = os.path.join(
    get_package_share_directory('robotics_vision_sim'), 'models'
) + ':' + os.environ.get('GAZEBO_MODEL_PATH', '')

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

    sim_pkg = get_package_share_directory('robotics_vision_sim')

    # Camera SDF
    camera_sdf_path = os.path.join(sim_pkg, 'urdf', 'camera.sdf')

    spawn_camera = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-file', camera_sdf_path, '-entity', 'camera'],
        output='screen'
    )

    camera_tf_broadcaster = Node(
        package='robotics_vision_sim',
        executable='camera_tf_broadcaster',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    pick_place_controller = Node(
        package='robotics_vision_sim',
        executable='pick_place_controller',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    vision_pipeline_node = Node(
        package='robotics_vision_sim',
        executable='vision_pipeline_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': True}  # ← IFRA-Cranfield uses True in Gazebo simulation
        ]
    )

    # world→base_link anchor (keeps MoveIt2 planning scene grounded)
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        output='log',
        arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'world', 'base_link'],
    )

    world_file = os.path.join(sim_pkg, 'worlds', 'pick_place.world')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={'world': world_file}.items()
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'ur3e'],
        output='screen'
    )

    # Controllers
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

    # MoveIt2 config
    robot_description_kinematics = load_yaml(sim_pkg, 'config/kinematics.yaml')

    robot_description_semantic = {
        'robot_description_semantic': load_file(sim_pkg, 'config/ur3e_robotiq_2f85.srdf')
    }

    moveit_controllers = {
        'moveit_simple_controller_manager': load_yaml(sim_pkg, 'config/moveit_controllers.yaml'),
        'moveit_controller_manager': 'moveit_simple_controller_manager/MoveItSimpleControllerManager',
    }

    trajectory_execution = {
        'moveit_manage_controllers': True,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }

    planning_scene_monitor_parameters = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
    }

    joint_limits = {
        'robot_description_planning': load_yaml(sim_pkg, 'config/joint_limits.yaml')
    }

    planning_pipelines = {
        'planning_pipelines': ['ompl'],
        'default_planning_pipeline': 'ompl',
        'ompl': load_yaml(sim_pkg, 'config/ompl_planning.yaml'),
    }

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            planning_pipelines,
            moveit_controllers,
            trajectory_execution,
            planning_scene_monitor_parameters,
            joint_limits,
            {'use_sim_time': True},
        ]
    )

    return LaunchDescription([
        gazebo,
        static_tf,
        robot_state_publisher,
        spawn_entity,
        spawn_camera,
        camera_tf_broadcaster,
        vision_pipeline_node,
        pick_place_controller,

        # CHANGE 2: Event-handler controller spawning — matches IFRA-Cranfield simulation.launch.py.
        # Controllers spawn only after spawn_entity exits (robot confirmed in Gazebo),
        # not on a fixed timer that may fire before Gazebo is ready.
        RegisterEventHandler(
            OnProcessExit(
                target_action=spawn_entity,
                on_exit=[
                    joint_state_broadcaster_spawner,
                    joint_trajectory_controller_spawner,
                    gripper_controller_spawner,
                ]
            )
        ),

        # CHANGE 3: move_group starts only after joint_trajectory_controller is confirmed active.
        # This guarantees MoveIt2 receives valid joint states from the first moment it starts,
        # preventing the "dirty robot state" error caused by move_group starting before
        # joint_state_broadcaster is publishing.
        RegisterEventHandler(
            OnProcessExit(
                target_action=joint_trajectory_controller_spawner,
                on_exit=[
                    TimerAction(
                        period=2.0,
                        actions=[move_group_node]
                    )
                ]
            )
        ),
    ])