import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import PoseStamped
from robotics_vision_sim_msgs.action import RunTask, PickPlace

TARGET_POSES = {
    'default': {
        'position': [-0.2, 0.4, 0.025],
        'orientation': [0.0, 0.707, 0.0, 0.707]
    }
}

class TaskManagerNode(Node):
    def __init__(self):
        super().__init__('task_manager_node')

        self.latest_object_pose = None
        self.latest_detection_time = None
        self.current_run_task_goal_handle = None  # store for feedback forwardin

        self.server_cb_group = ReentrantCallbackGroup()
        self.client_cb_group = ReentrantCallbackGroup()

        self.create_subscription(
            PoseStamped,
            'vision/object_pose',
            self.object_pose_callback,
            10
        )

        self.run_task_server = ActionServer(
            self,
            RunTask,
            'run_task',
            execute_callback=self.execute_callback,
            callback_group=self.server_cb_group,
        )

        self.pick_place_client = ActionClient(
            self,
            PickPlace,
            'pick_place',
            callback_group=self.client_cb_group         
        )

    def object_pose_callback(self, msg:PoseStamped):
        self.latest_object_pose = msg  # store full PoseStamped, not just msg.pose
        self.latest_detection_time = self.get_clock().now()

    def _pick_place_feedback_cb(self, feedback_msg):
        if self.current_run_task_goal_handle is None:
            return
        feedback = RunTask.Feedback()
        feedback.current_stage = feedback_msg.feedback.current_stage
        feedback.status_message = feedback_msg.feedback.status_message
        self.current_run_task_goal_handle.publish_feedback(feedback)

    def execute_callback(self, goal_handle:ServerGoalHandle):

        start_time = time.time()
        goal = goal_handle.request  # has object_id and target_id
        result = RunTask.Result()
        feedback = RunTask.Feedback()

        # Guard — abort if detection too old
        MAX_DETECTION_AGE_SEC = 2.0
        

        if self.latest_object_pose is None:
            result.status = RunTask.Result.STATUS_FAILURE
            result.message = 'No object detected yet'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result
        
        age = (self.get_clock().now() - self.latest_detection_time).nanoseconds / 1e9
        self.get_logger().info(f'Detection age: {age:.2f}s')

        if age > MAX_DETECTION_AGE_SEC:
            result.status = RunTask.Result.STATUS_FAILURE
            result.message = f'Detection is {age:.1f}s old — too stale to act on'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result

        target_data = TARGET_POSES.get(goal.target_id)

        if target_data is None:
            result.status = RunTask.Result.STATUS_FAILURE
            result.message = f'Unknown target_id: {goal.target_id}'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result

        target_pose = PoseStamped()

        target_pose.header.frame_id = 'base_link'
        target_pose.header.stamp = self.get_clock().now().to_msg()

        target_pose.pose.position.x = target_data['position'][0]
        target_pose.pose.position.y = target_data['position'][1]
        target_pose.pose.position.z = target_data['position'][2]
        target_pose.pose.orientation.x = target_data['orientation'][0]
        target_pose.pose.orientation.y = target_data['orientation'][1]
        target_pose.pose.orientation.z = target_data['orientation'][2]
        target_pose.pose.orientation.w = target_data['orientation'][3]

        pick_place_goal = PickPlace.Goal()

        pick_place_goal.object_id = goal.object_id
        pick_place_goal.object_pose = self.latest_object_pose
        pick_place_goal.target_pose = target_pose
        pick_place_goal.gripper_width = 0.05

        self.current_run_task_goal_handle = goal_handle

        send_goal_future = self.pick_place_client.send_goal_async(
            pick_place_goal,
            feedback_callback=self._pick_place_feedback_cb,
            )
        rclpy.spin_until_future_complete(self, send_goal_future)
        pick_place_goal_handle = send_goal_future.result()  

        if not pick_place_goal_handle.accepted:
            result.status = RunTask.Result.STATUS_FAILURE
            result.message = 'pick_place goal rejected'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result
        
        result_future = pick_place_goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        pick_place_result = result_future.result().result

        self.current_run_task_goal_handle = None

        if pick_place_result.status == PickPlace.Result.STATUS_SUCCESS:
            result.status = RunTask.Result.STATUS_SUCCESS
            result.message = 'run task successful'
            result.total_time_sec = time.time() - start_time
            goal_handle.succeed()
            return result
        
        elif pick_place_result.status == PickPlace.Result.STATUS_ABORTED:
            result.status = RunTask.Result.STATUS_ABORTED
            result.message = 'run task aborted'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result
        
        elif pick_place_result.status == PickPlace.Result.STATUS_FAILURE:
            result.status = RunTask.Result.STATUS_FAILURE
            result.message = 'run task failed'
            result.total_time_sec = time.time() - start_time
            goal_handle.abort()
            return result


def main(args=None):
    rclpy.init(args=args)
    node = TaskManagerNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()