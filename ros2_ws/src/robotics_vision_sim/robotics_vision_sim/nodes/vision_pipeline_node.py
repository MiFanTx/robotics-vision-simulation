import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
from scipy.spatial.transform import Rotation


class VisionPipelineNode(Node):

    def __init__(self):
        super().__init__('vision_pipeline_node')

        self.bridge = CvBridge()

        # Camera intrinsics derived from SDF (fov=1.047, 640x480)
        self.camera_matrix = np.array([
            [1108.52, 0,       640.0],
            [0,       1108.52, 480.0],
            [0,       0,       1.0  ]
        ], dtype=np.float32)

        self.dist_coeffs = np.zeros((4, 1), dtype=np.float32)

        # ArUco setup
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.parameters = cv2.aruco.DetectorParameters_create()
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 23
        self.parameters.adaptiveThreshWinSizeStep = 10
        self.parameters.minMarkerPerimeterRate = 0.005
        self.parameters.maxMarkerPerimeterRate = 4.0
        self.parameters.polygonalApproxAccuracyRate = 0.05
        self.parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX 
        self.parameters.adaptiveThreshConstant = 7

        # Marker physical size in metres (matches box face: 0.05m)
        self.marker_size = 0.05

        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        self.pose_pub = self.create_publisher(
            PoseStamped,
            '/vision/marker_pose',
            10
        )

        self.get_logger().info('VisionPipelineNode ready')

    def image_callback(self, msg):
        image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.dictionary, parameters=self.parameters)

        self.get_logger().info(
        f'Detected: {ids.flatten() if ids is not None else "none"}, '
        f'Rejected: {len(rejected)}',
        throttle_duration_sec=2.0)

        if ids is None:
            return
        
        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, self.marker_size, self.camera_matrix, self.dist_coeffs)

        for i, marker_id in enumerate(ids.flatten()):
            if marker_id == 0:
                msg = PoseStamped()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = 'camera_link'

                msg.pose.position.x = tvecs[i][0][0]
                msg.pose.position.y = tvecs[i][0][1]
                msg.pose.position.z = tvecs[i][0][2]

                rotation_matrix, _ = cv2.Rodrigues(rvecs[i])

                r = Rotation.from_matrix(rotation_matrix)
                q = r.as_quat()

                msg.pose.orientation.x = q[0]
                msg.pose.orientation.y = q[1]
                msg.pose.orientation.z = q[2]
                msg.pose.orientation.w = q[3]

                self.pose_pub.publish(msg)

                break

        pass


def main(args=None):
    rclpy.init(args=args)
    node = VisionPipelineNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()