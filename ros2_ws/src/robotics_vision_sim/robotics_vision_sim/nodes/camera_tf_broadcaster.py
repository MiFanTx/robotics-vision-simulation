import rclpy
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster, TransformStamped


class CameraTFBroadcaster (Node):

    def __init__(self):
        super().__init__('camera_broadcaster')

        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self.publish_static_transform()

        self.get_logger().info('Camera Static Transform Published!')

    def publish_static_transform(self):
        t = TransformStamped()

        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'camera_link'

        t.transform.translation.x = 0.5
        t.transform.translation.y = 0.5
        t.transform.translation.z = 1.0

        t.transform.rotation.w = 1.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = CameraTFBroadcaster()

    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()



    
