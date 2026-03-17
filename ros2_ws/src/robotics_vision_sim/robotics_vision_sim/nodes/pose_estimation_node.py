import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import tf2_ros
import tf2_geometry_msgs  # needed for do_transform_pose

class PoseEstimationNode(Node):
    def __init__(self):
        super().__init__('pose_estimation_node')
        
        # TF2 setup
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        self.sub = self.create_subscription(
            PoseStamped,
            '/vision/marker_pose',
            self.marker_pose_callback,
            10
        )

        self.pub = self.create_publisher(
            PoseStamped,
            '/vision/object_pose',
            10
        )
        

    def marker_pose_callback(self, msg: PoseStamped):
        try:
            transformed = self.tf_buffer.transform(msg, 'base_link')

            self.pub.publish(transformed)
        except Exception as e:
            self.get_logger().warn(f'Transform failed: {e}')

def main(args=None):
        rclpy.init(args=args)
        node = PoseEstimationNode()
        rclpy.spin(node)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()