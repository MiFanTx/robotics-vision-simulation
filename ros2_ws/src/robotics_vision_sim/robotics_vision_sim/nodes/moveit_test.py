from threading import Thread

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from pymoveit2 import MoveIt2
from pymoveit2.robots import ur as robot

def main():
    rclpy.init()
    node = Node("moveit_test")
    callback_group = ReentrantCallbackGroup()

    moveit2 = MoveIt2(
        node=node,
        joint_names=robot.joint_names(),
        base_link_name=robot.base_link_name(),
        end_effector_name=robot.end_effector_name(),
        group_name=robot.MOVE_GROUP_ARM,
        callback_group=callback_group,
        use_move_group_action=True
    )

    # TODO 2: Create an executor, add the node, and spin it
    # Hint: you did this in Chapter 7 with action servers
    # Use MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor_thread = Thread(target=executor.spin, daemon=True, args=())
    executor_thread.start()

    # TODO 3: Move to the named "home" position
    # Hint: pymoveit2 has a method called move_to_configuration()
    # The named states from the SRDF can be used here
    moveit2.move_to_configuration(
        joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
    )

    executor_thread.join()

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()