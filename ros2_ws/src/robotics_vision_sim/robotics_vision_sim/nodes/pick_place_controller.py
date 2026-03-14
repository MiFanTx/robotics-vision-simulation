import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from pymoveit2 import MoveIt2
from pymoveit2.robots import ur as robot
from sensor_msgs.msg import JointState

from robotics_vision_sim_msgs.action import PickPlace
from control_msgs.action import GripperCommand
from linkattacher_msgs.srv import AttachLink, DetachLink


class PickPlaceController(Node):

    def __init__(self):
        super().__init__('pick_place_controller')

        self.pre_grasp_ee_pose = None
        self.pre_place_ee_pose = None

        self.safe_height = 0.05 # the stopping distance above the object in meter

        # Separate Callback Group for action and client
        self.action_cb_group = ReentrantCallbackGroup()
        self.client_cb_group = ReentrantCallbackGroup()

        self.action_server = ActionServer(
            self,
            PickPlace,
            'pick_place',
            execute_callback=self.execute_callback,
            callback_group=self.action_cb_group,
        )

        self.moveit2 = MoveIt2(
            node=self,
            joint_names=robot.joint_names(),
            base_link_name=robot.base_link_name(),
            end_effector_name='EE_robotiq_2f85',
            group_name='ur_manipulator',
            callback_group=self.client_cb_group,
            use_move_group_action=True
        )

        # MoveIt2 Configuration
        self.moveit2.max_velocity = 0.5
        self.moveit2.max_acceleration = 0.5

        self.moveit2.planner_id = 'RRTConnect'
        self.moveit2.pipeline_id = 'ompl'

        self.moveit2.allowed_planning_time = 5.0
        
        # Initialise Clients
        self.gripper_client = ActionClient(
            self,
            GripperCommand,
            '/gripper_controller/gripper_cmd',
            callback_group=self.client_cb_group
        )

        self.attach_client = self.create_client(
            AttachLink,
            '/ATTACHLINK',
            callback_group=self.client_cb_group
        )

        self.detach_client = self.create_client(
            DetachLink,
            '/DETACHLINK',
            callback_group=self.client_cb_group
        )

        # Joint State
        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self._joint_state_cb,
            10,
            callback_group=self.action_cb_group
        )

        self.joint_state_ready = False


    def _joint_state_cb(self, msg):
        if not self.joint_state_ready and len(msg.position) > 0:
            self.joint_state_ready = True
            self.get_logger().info('Joint states ready')

            self.get_logger().info('PickPlaceController ready')


    def _execute_motion(self, move_fn, stage_name, max_retries=5):
        for attempt in range(max_retries):
            move_fn()
            if self.moveit2.wait_until_executed():
                return True
            self.get_logger().warn(
                f'{stage_name} attempt {attempt + 1}/{max_retries} failed, retrying...'
            )
            time.sleep(1.0)
        return False

    def execute_callback(self, goal_handle:ServerGoalHandle):
        self.get_logger().info('Pick-place goal received')

        # Wait for joint states to be valid
        timeout = 10.0
        start = time.time()
        while not self.joint_state_ready:
            if time.time() - start > timeout:
                result.status = PickPlace.Result.STATUS_FAILURE
                result.message = 'Timed out waiting for joint states'
                goal_handle.abort()
                return result
            time.sleep(0.1)
        
        # Initialise 
        feedback = PickPlace.Feedback()
        result = PickPlace.Result()
        start_time = time.time()
        goal = goal_handle.request

        # Check if the object is in valid frame
        if goal.object_pose.header.frame_id != 'base_link':
            result.status = PickPlace.Result.STATUS_FAILURE
            result.message = f'Expected pose in base link, got {goal.object_pose.header.frame_id}'
            goal_handle.abort()
            return result


        stages = [
            ('MOVING_TO_OBJECT',   'Moving to pick position...'),
            ('LOWERING_TO_OBJECT', 'Lowering to object...'),
            ('GRASPING',           'Closing gripper...'),
            ('LIFTING',            'Lifting object...'),
            ('MOVING_TO_TARGET',   'Moving to place position...'),
            ('LOWERING_TO_TARGET', 'Lowering to target...'),
            ('PLACING',            'Opening gripper...'),
            ('RETREATING',         'Retreating to safe position...'),
            ('HOMING',             'Returning to home...'),
        ]

        total_stages = len(stages)

        # Get object and target pose info
        obj_pos = goal.object_pose.pose.position
        obj_ori = goal.object_pose.pose.orientation
        tgt_pos = goal.target_pose.pose.position
        tgt_ori = goal.target_pose.pose.orientation

        obj_safe_z = obj_pos.z + self.safe_height
        tgt_safe_z = tgt_pos.z + self.safe_height

        # loop through the stages
        for step, (stage_name, status_msg) in enumerate(stages, start=1):

            # publish the current stage info
            feedback.current_stage = stage_name
            feedback.status_message = f'[{step}/{total_stages}] {status_msg}'
            goal_handle.publish_feedback(feedback)
            self.get_logger().info(f'  [{step}/{total_stages}] {stage_name}: {status_msg}')

            # check for cancel request
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.status = PickPlace.Result.STATUS_CANCELED
                result.message = f'Pick and Place canceled at {stage_name}'
                result.total_time_sec = time.time() - start_time
                self.get_logger().info(f'Goal canceled during {stage_name}')
                return result

            # --- MOTION STAGES ---
            if stage_name == 'MOVING_TO_OBJECT':

                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[obj_pos.x, obj_pos.y, obj_safe_z],
                        quat_xyzw=[obj_ori.x, obj_ori.y, obj_ori.z, obj_ori.w]
                    ), stage_name)

                if success:
                    # Get actual EE pose after arriving
                    self.pre_grasp_ee_pose = self.moveit2.compute_fk(fk_link_names=['EE_robotiq_2f85'])

            elif stage_name == 'LOWERING_TO_OBJECT':

                pose = self.pre_grasp_ee_pose[0].pose

                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, pose.position.z - self.safe_height],
                        quat_xyzw=[pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                        cartesian=True, cartesian_fraction_threshold=0.95
                    ), stage_name)
                
            elif stage_name == 'GRASPING':
                gripper_goal = GripperCommand.Goal()
                gripper_goal.command.position = 0.0
                gripper_goal.command.max_effort = 10.0
                future = self.gripper_client.send_goal_async(gripper_goal)
                rclpy.spin_until_future_complete(self, future)

                attach_req = AttachLink.Request()
                attach_req.model1_name = 'ur3e'
                attach_req.link1_name = 'EE_robotiq_2f85'
                attach_req.model2_name = goal.object_id
                attach_req.link2_name = goal.object_id
                future = self.attach_client.call_async(attach_req)
                rclpy.spin_until_future_complete(self, future)
                continue

            elif stage_name == 'LIFTING':

                pose = self.pre_grasp_ee_pose[0].pose

                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, pose.position.z],
                        quat_xyzw=[pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                        cartesian=True, cartesian_fraction_threshold=0.95
                    ), stage_name)
                
            elif stage_name == 'MOVING_TO_TARGET':
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[tgt_pos.x, tgt_pos.y, tgt_safe_z],
                        quat_xyzw=[tgt_ori.x, tgt_ori.y, tgt_ori.z, tgt_ori.w]
                    ), stage_name)
                if success:
                    self.pre_place_ee_pose = self.moveit2.compute_fk(fk_link_names=['EE_robotiq_2f85'])

            elif stage_name == 'LOWERING_TO_TARGET':
                pose = self.pre_place_ee_pose[0].pose
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, pose.position.z - self.safe_height],
                        quat_xyzw=[pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                        cartesian=True, cartesian_fraction_threshold=0.95
                    ), stage_name)

            elif stage_name == 'PLACING':
                detach_req = DetachLink.Request()
                detach_req.model1_name = 'ur3e'
                detach_req.link1_name = 'EE_robotiq_2f85'
                detach_req.model2_name = goal.object_id
                detach_req.link2_name = goal.object_id
                future = self.detach_client.call_async(detach_req)
                rclpy.spin_until_future_complete(self, future)

                gripper_goal = GripperCommand.Goal()
                gripper_goal.command.position = 0.8
                gripper_goal.command.max_effort = 10.0
                future = self.gripper_client.send_goal_async(gripper_goal)
                rclpy.spin_until_future_complete(self, future)
                continue

            elif stage_name == 'RETREATING':
                pose = self.pre_place_ee_pose[0].pose  # reuse pre-place FK
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, pose.position.z],
                        quat_xyzw=[pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                        cartesian=True, cartesian_fraction_threshold=0.95
                    ), stage_name)

            elif stage_name == 'HOMING':
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_configuration(
                        joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                    ), stage_name)

            if not success:
                self._execute_motion(
                    lambda: self.moveit2.move_to_configuration(
                        joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                    ), 'HOMING')
                result.status = PickPlace.Result.STATUS_ABORTED
                result.message = f'Pick and place aborted at stage {stage_name}'
                result.total_time_sec = time.time() - start_time
                goal_handle.abort()
                return result

        result.status = PickPlace.Result.STATUS_SUCCESS
        result.message = ''
        result.total_time_sec = time.time() - start_time
        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)
    node = PickPlaceController()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()
        