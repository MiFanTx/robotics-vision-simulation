import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from pymoveit2 import MoveIt2
from pymoveit2.robots import ur as robot

from robotics_vision_sim_msgs.action import PickPlace

from threading import Thread, Event



class PickPlaceController(Node):
    
    def __init__(self):
        super().__init__('pick_place_server')
        
        self.safe_height = 0.05

        self.callback_group = ReentrantCallbackGroup()
        self.moveit2_callback_group = ReentrantCallbackGroup()


        self.action_server = ActionServer(
            self,
            PickPlace,
            'pick_place',
            execute_callback=self.executable_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group
        )

        self.moveit2 = MoveIt2(
            node=self,
            joint_names=robot.joint_names(),
            base_link_name=robot.base_link_name(),
            end_effector_name=robot.end_effector_name(),
            group_name=robot.MOVE_GROUP_ARM,
            callback_group=self.moveit2_callback_group,
            use_move_group_action=True
        )

        self.moveit2.max_velocity = 0.5
        self.moveit2.max_acceleration = 0.5

        # In __init__, replace the add_collision_box call with:
        self.create_timer(2.0, self._setup_planning_scene)
        self._scene_setup_done = False

        self.get_logger().info('Pick and Place Controller Initialised!')

    def _setup_planning_scene(self):
        if self._scene_setup_done:
            return
        self.moveit2.add_collision_box(
            id='ground',
            size=[2.0, 2.0, 0.01],
            position=[0.0, 0.0, -0.005],
            frame_id='world'
        )
        self._scene_setup_done = True
        self.get_logger().info('Planning scene setup complete')

    def goal_callback(self, goal_request: PickPlace.Goal):
        self.get_logger().info(f'Received goal requestion for object: {goal_request.object_id}')
        return GoalResponse.ACCEPT
    
    def cancel_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info('Received cancel request')
        return CancelResponse.ACCEPT
    
    async def executable_callback(self, goal_handle: ServerGoalHandle):

        time.sleep(3)


        self.get_logger().info(f'Received goal: Pick "{goal_handle.request.object_id}"')
        feedback = PickPlace.Feedback()

        stages = [
            ('MOVING_TO_OBJECT', 20.0, 'Moving to pick position...'),
            ('LOWERING_TO_OBJECT', 30.0, 'Lowering to object...'),
            ('GRASPING', 40.0, 'Closing gripper...'),
            ('LIFTING', 50.0, 'Lifting object...'),
            ('MOVING_TO_TARGET', 60.0, 'Moving to place position...'),
            ('LOWERING_TO_TARGET', 70.0, 'Lowering to target...'),            
            ('PLACING', 80.0, 'Opening gripper...'),
            ('RETREATING', 90.0, 'Retreating to safe position...'),
            ('HOMING', 100.0, 'Backing to home...'),
        ]

        start_time = time.time()

        obj_pos = goal_handle.request.object_pose.pose.position
        obj_ori = goal_handle.request.object_pose.pose.orientation
        tgt_pos = goal_handle.request.target_pose.pose.position
        tgt_ori = goal_handle.request.target_pose.pose.orientation

        obj_safe_z = obj_pos.z + self.safe_height
        tgt_safe_z = tgt_pos.z + self.safe_height

        for stage_name, progress, status_msgs in stages:

            if goal_handle.is_cancel_requested:
                goal_handle.canceled()

                result = PickPlace.Result()
                result.status = PickPlace.Result.STATUS_CANCELED
                result.message = f'Pick and Place canceled at {stage_name}'
                result.total_time_sec = time.time() - start_time

                self.get_logger().info(f'Goal canceled during {stage_name}')
                return result
            
            feedback.current_stage = stage_name
            feedback.progress_percent = progress
            feedback.status_message = status_msgs

            goal_handle.publish_feedback(feedback)
            self.get_logger().info(f'  [{progress:.0f}%] {stage_name}: {status_msgs}')

            if stage_name == 'MOVING_TO_OBJECT':
                self.get_logger().info(f'Planning pose: frame={goal_handle.request.object_pose.header.frame_id}, pos=[{obj_pos.x}, {obj_pos.y}, {obj_pos.z}]')
                self.moveit2.move_to_pose(
                    position=[obj_pos.x, obj_pos.y, obj_safe_z],
                    quat_xyzw=[obj_ori.x, obj_ori.y, obj_ori.z, obj_ori.w]
                )

            elif stage_name == 'LOWERING_TO_OBJECT':
                self.moveit2.move_to_pose(
                    position=obj_pos,
                    quat_xyzw=obj_ori
                )
            
            elif stage_name == 'GRASPING':
                continue

            elif stage_name == 'LIFTING':
                self.moveit2.move_to_pose(
                    position=[obj_pos.x, obj_pos.y, obj_safe_z],
                    quat_xyzw=[obj_ori.x, obj_ori.y, obj_ori.z, obj_ori.w]
                )

            elif stage_name == 'MOVING_TO_TARGET':
                self.moveit2.move_to_pose(
                    position=[tgt_pos.x, tgt_pos.y, tgt_safe_z],
                    quat_xyzw=[tgt_ori.x, tgt_ori.y, tgt_ori.z, tgt_ori.w]
                )
            
            elif stage_name == 'LOWERING_TO_TARGET':
                self.moveit2.move_to_pose(
                    position=tgt_pos, 
                    quat_xyzw=tgt_ori
                )
            
            elif stage_name == 'PLACING':
                continue

            elif stage_name == 'RETREATING':
                self.moveit2.move_to_pose(
                    position=[tgt_pos.x, tgt_pos.y, tgt_safe_z],
                    quat_xyzw=[tgt_ori.x, tgt_ori.y, tgt_ori.z, tgt_ori.w]
                )

            elif stage_name == 'HOMING':
                self.moveit2.move_to_configuration(
                    joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                ) # move back home

            success = self.moveit2.wait_until_executed()
            time.sleep(1)
            if not success:
                goal_handle.abort()
                self.moveit2.move_to_configuration(
                    joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                ) # move back home
                self.moveit2.wait_until_executed()
                result = PickPlace.Result()
                result.status = PickPlace.Result.STATUS_ABORTED
                result.message = f'Pick and place aborted at stage {stage_name}'
                result.total_time_sec = time.time() - start_time
                return result

        result = PickPlace.Result()
        result.status = PickPlace.Result.STATUS_SUCCESS
        result.message = 'Pick and place completed successfully'
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

if __name__ == '__main__':
    main()

