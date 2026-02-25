import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from robotics_vision_sim_msgs.action import PickPlace

class PickPlaceController(Node):
    
    def __init__(self):
        super().__init__('pick_place_server')

        self.callback_group = ReentrantCallbackGroup()

        self.action_server = ActionServer(
            self,
            PickPlace,
            'pick_place',
            execute_callback=self.executable_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group
        )

        self.get_logger().info('Pick and Place Controller Initialised!')

    def goal_callback(self, goal_request: PickPlace.Goal):
        self.get_logger().info(f'Received goal requestion for object: {goal_request.object_id}')
        return GoalResponse.ACCEPT
    
    def cancel_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info('Received cancel request')
        return CancelResponse.ACCEPT
    
    def executable_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info(f'Received goal: Pick "{goal_handle.request.object_id}"')
        feedback = PickPlace.Feedback()

        stages = [
            ('MOVING_TO_OBJECT', 20.0, 'Moving to pick position...'),
            ('LOWERING', 30.0, 'Lowering to object...'),
            ('GRASPING', 40.0, 'Closing gripper...'),
            ('LIFTING', 50.0, 'Lifting object...'),
            ('MOVING_TO_TARGET', 60.0, 'Moving to place position...'),
            ('LOWERING', 70.0, 'Lowering to target...'),            
            ('PLACING', 80.0, 'Opening gripper...'),
            ('RETREATING', 100.0, 'Retreating to safe position...'),
        ]

        start_time = time.time()

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

        result = PickPlace.Result()
        result.status = PickPlace.Result.STATUS_SUCCESS
        result.message = 'Pick and place completed successfully'
        result.total_time_sec = time.time() - start_time

        goal_handle.succeed()
        return result
    
def main(args=None):
    rclpy.init(args=args)
    node = PickPlaceController()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

