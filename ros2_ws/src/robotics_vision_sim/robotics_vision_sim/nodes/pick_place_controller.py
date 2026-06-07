import time
import math

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

        # Pose for Cartesian movement
        self.pre_grasp_ee_pose = None
        self.pre_place_ee_pose = None

        self.safe_height = 0.05 # the stopping distance above the object in meter

        # --- Scene assumptions (named on purpose) ----------------------------------
        # ArUco's z (the camera optical axis) is the noisiest axis of the marker pose,
        # and we already KNOW the object's height and the plane it rests on. So we take
        # x,y from vision and DERIVE z from geometry. Valid only while these hold:
        self.surface_z = 0.0    # ground_plane height (worlds/pick_place.world) — objects rest here
        self.box_height = 0.05  # aruco_box edge length (models/aruco_box/model.sdf)
        # FUTURE: per-object height (multi-object) + per-target surface height (tables) — see roadmap.

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

    def _wait_for_future(self, future, timeout=5.0):
        """Wait for a future by spinning THIS node ourselves.

        We cannot rely on the background MultiThreadedExecutor to complete this future.
        pymoveit2's helpers (wait_until_executed / compute_fk / compute_ik) call
        `rclpy.spin_once(self._node)` with no executor, which defaults to the GLOBAL
        executor; add_node then evicts our node from the MTE (a node has exactly one
        owner). So after the first MoveIt call in this callback, the MTE no longer holds
        our node and its threads service nothing for us — a non-spinning poll would never
        see the future complete and would always burn the full timeout (the 10s gripper
        stages we diagnosed). Fix: drive the future the same way pymoveit2 does, by
        spinning our own node until the response lands. Safe here because the gripper/
        attach/detach clients are created in __init__ (fully registered), not lazily
        mid-callback (the case that caused gotcha #18's hang).
        """
        start = time.time()
        while not future.done():
            if time.time() - start > timeout:
                break
            rclpy.spin_once(self, timeout_sec=0.1)

        return future.done()

    def execute_callback(self, goal_handle:ServerGoalHandle):
        self.get_logger().info('Pick-place goal received')

        # Initialise 
        feedback = PickPlace.Feedback()
        result = PickPlace.Result()
        goal = goal_handle.request

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

        # Fix gripper orientation to always pointing down
        obj_ori.x = 0.0
        obj_ori.y = 0.707
        obj_ori.z = 0.0
        obj_ori.w = 0.707

        # Override the noisy marker z with a geometry-derived height (x,y stay from vision).
        # The box of height self.box_height rests on self.surface_z, so its centre and a
        # robust grasp height are both known without trusting the marker's depth axis.
        # TODO(grasp-z): derive these two from self.surface_z and self.box_height —
        box_center_z =  self.surface_z + self.box_height * 0.5       # geometric centre of the box on the surface
        grasp_z      = box_center_z        # TCP grasp height (the box centre is a robust choice)
        obj_pos.z    = grasp_z    # feed it into the existing approach (obj_safe_z) + descent
        # box_center_z is reused by the collision box below; grasp_z is reused by
        # LOWERING_TO_TARGET so the box is set down at the height it was picked from.

        obj_safe_z = obj_pos.z + self.safe_height
        tgt_safe_z = tgt_pos.z + self.safe_height

        # --- Register the box in MoveIt's planning scene ----------------------------
        # OMPL only avoids what is IN the planning scene; the Gazebo box is invisible to
        # it, so the stage-1 reach plans straight through and knocks it. Add the box as a
        # WORLD collision object here so OMPL routes around it. (It changes role later:
        # attached at GRASPING, removed at PLACING — see those stages.)
        # TODO(scene-add): add a 0.05^3 collision box at the box CENTRE.
        #   - size comes from model.sdf: (0.05, 0.05, 0.05)
        #   - obj_pos.z was just shifted DOWN by GRASP_Z_OFFSET to the grasp point. Decide
        #     what z the box CENTRE should be (the marker sits on the top face) — a wrong
        #     centre means OMPL avoids the wrong volume.
        self.moveit2.add_collision_box(
            id=goal.object_id, size=(0.05, 0.05, 0.05),
            # TODO(grasp-z): the collision box centre is box_center_z (x,y from vision, z
            # from geometry) — the old `obj_pos.z + 0.015` assumed the marker-offset z.
            position=[obj_pos.x, obj_pos.y, box_center_z],
            quat_xyzw=[obj_ori.x, obj_ori.y, obj_ori.z, obj_ori.w],
            frame_id='base_link')
        
        time.sleep(0.2) # wait for collision box to be added

        self.get_logger().info(
            f'Object pose: x={obj_pos.x:.3f}, y={obj_pos.y:.3f}, z={obj_pos.z:.3f}'
        )
        self.get_logger().info(
            f'Approach z: {obj_pos.z + self.safe_height:.3f}, Grasp z: {obj_pos.z:.3f}'
        )

        

        # TODO(scene-settle): add_collision_box PUBLISHES and returns immediately. move_group
        #   (a separate process) needs a beat to receive + apply it before stage 1 plans, or
        #   OMPL plans against the still-empty scene. Give it a short settle here.

        
        start_time = time.time()

        # loop through the stages
        for step, (stage_name, status_msg) in enumerate(stages, start=1):

            # publish the current stage info
            feedback.current_stage = stage_name
            feedback.status_message = f'[{step}/{total_stages}] {status_msg}'
            goal_handle.publish_feedback(feedback)
            self.get_logger().info(f'  [{step}/{total_stages}] {stage_name}: {status_msg}')
            success = False

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
                    fk = self.pre_grasp_ee_pose[0].pose
                    self.get_logger().info(
                        f'Pre-grasp EE: x={fk.position.x:.3f}, y={fk.position.y:.3f}, z={fk.position.z:.3f}'
                    )

            elif stage_name == 'LOWERING_TO_OBJECT':

                pose = self.pre_grasp_ee_pose[0].pose # QUESTION: why move to ee instead of object pose

                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, pose.position.z - self.safe_height],
                        quat_xyzw=[pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                        cartesian=True, cartesian_fraction_threshold=0.95
                    ), stage_name)
                
            elif stage_name == 'GRASPING':
                self.get_logger().info(f'Attaching: model={goal.object_id}, link={goal.object_id}')
                gripper_goal = GripperCommand.Goal()
                gripper_goal.command.position = 0.0
                gripper_goal.command.max_effort = 10.0
                future = self.gripper_client.send_goal_async(gripper_goal)
                self._wait_for_future(future)

                attach_req = AttachLink.Request()
                attach_req.model1_name = 'ur3e'
                attach_req.link1_name = 'EE_robotiq_2f85'
                attach_req.model2_name = goal.object_id
                attach_req.link2_name = goal.object_id
                future = self.attach_client.call_async(attach_req)
                self._wait_for_future(future)
                attach_result = future.result()
                self.get_logger().info(f'Attach result: {attach_result}')

                # The box is now held. Tell MoveIt it's part of the robot so (a) the closed
                # fingers touching it don't read as a collision and (b) LIFTING knows the box
                # rose WITH the arm instead of leaving a phantom box on the ground for the
                # planner to crash into.
                # TODO(scene-attach): attach the collision object to the gripper.
                self.moveit2.attach_collision_object(
                    id=goal.object_id, link_name='EE_robotiq_2f85', touch_links=[
                        'robotiq_85_base_link',
                        'robotiq_85_left_knuckle_link', 'robotiq_85_right_knuckle_link',
                        'robotiq_85_left_inner_knuckle_link', 'robotiq_85_right_inner_knuckle_link',
                        'robotiq_85_left_finger_link', 'robotiq_85_right_finger_link',
                        'robotiq_85_left_finger_tip_link', 'robotiq_85_right_finger_tip_link'])
                #   touch_links = the gripper finger links allowed to contact the box. Find
                #   their exact names by introspection (URDF / joint_states) — the stage-5
                #   self-collision error named one of them.
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
                # Stage 5 = move between KNOWN endpoints (holding the object -> fixed place
                # target). THIS is PILZ PTP's job: deterministic, repeatable, near-straight.
                # We resolve the above-target POSE -> a vetted JOINT config ourselves and PTP
                # to the config, so PILZ can't substitute a wrist-flipped IK solution of its
                # own. This is the stage that proves the IK + PILZ pipeline actually works.
                #
                # Switch the planner to PILZ PTP for this stage.
                self.moveit2.pipeline_id = 'pilz_industrial_motion_planner'
                self.moveit2.planner_id = 'PTP'
                # Resolve the above-target POSE -> a joint config via the SYNC compute_ik
                # (not async+poll). Same reason compute_fk works everywhere here: the sync
                # call spin_once()s the node ITSELF to drive its own future, so it does NOT
                # depend on the MTE seeing a cleanly-registered client — which the
                # wait_until_executed spin corrupts. Safe in our serial single-callback flow
                # (compute_fk proves it); gotcha #16's __enter__ crash needs concurrent
                # spinning, which doesn't happen on this standalone call.


                # The place is the pick rotated ~90deg about the base (same radius/height), so
                # the clean IK solution is "start config, base pre-rotated by Δθ". KDL is a
                # local solver: from a cold seed it can jump to a contorted basin that PTP then
                # sweeps through the upper arm (self-collision). So SEED it into the right basin
                # — current joints with shoulder_pan advanced by the pick->place bearing change
                # — and KDL converges to the near-start solution PTP can sweep cleanly.
                pick = self.pre_grasp_ee_pose[0].pose.position    # EE above the object
                d_theta = math.atan2(tgt_pos.y, tgt_pos.x) - math.atan2(pick.y, pick.x)
                cur = self.moveit2.joint_state
                m = dict(zip(cur.name, cur.position))
                seed = [m[j] for j in self.moveit2.joint_names]
                seed[0] += d_theta                                # pre-rotate the base

                target_config = self.moveit2.compute_ik(
                    position=[tgt_pos.x, tgt_pos.y, tgt_safe_z],
                    quat_xyzw=[tgt_ori.x, tgt_ori.y, tgt_ori.z, tgt_ori.w],
                    start_joint_state=seed,
                )

                if target_config is None:
                    self.get_logger().error(f'Failed to compute IK at {stage_name}')
                    success = False
                else:
                    name_to_pose = dict(zip(target_config.name, target_config.position))
                    arm_pos = [name_to_pose[i] for i in self.moveit2.joint_names]

                    success = self._execute_motion(
                        lambda: self.moveit2.move_to_configuration(arm_pos), stage_name=stage_name
                    )

                if success:
                    # KEEP: LOWERING_TO_TARGET reads pre_place_ee_pose.
                    self.pre_place_ee_pose = self.moveit2.compute_fk(fk_link_names=['EE_robotiq_2f85'])

            elif stage_name == 'LOWERING_TO_TARGET':
                pose = self.pre_place_ee_pose[0].pose
                # Set the box DOWN, don't drive it into the floor. Reuse the grasp height:
                # the box rested on the surface at grasp_z, so returning the TCP there rests
                # it again. Valid while place surface == pick surface; the general form is
                # grasp_z + (place_surface_z - pick_surface_z).
                # TODO(place-z): use grasp_z for the z below, not pose.position.z - self.safe_height.
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_pose(
                        position=[pose.position.x, pose.position.y, grasp_z],
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
                self._wait_for_future(future)

                # Box released in Gazebo; now sync MoveIt's scene: detach it from the robot
                # AND remove it from the world so it stops being an obstacle / phantom on the
                # next move. (Leave it attached and HOMING would route around a box that's no
                # longer on the gripper.)
                # TODO(scene-detach): detach the attached object, then remove the world object.
                self.moveit2.detach_collision_object(goal.object_id)
                self.moveit2.remove_collision_object(goal.object_id)

                gripper_goal = GripperCommand.Goal()
                gripper_goal.command.position = 0.8
                gripper_goal.command.max_effort = 10.0
                future = self.gripper_client.send_goal_async(gripper_goal)
                self._wait_for_future(future)
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
                # Homing from the (elevated, known) retreat pose back to a fixed config.
                # Stage 5 left the planner on PILZ PTP, so reset to OMPL here: homing is an
                # adaptive reach that should route around the floor, not a blind PTP line.
                self.moveit2.pipeline_id = 'ompl'
                self.moveit2.planner_id  = 'RRTConnect'
                success = self._execute_motion(
                    lambda: self.moveit2.move_to_configuration(
                        joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                    ), stage_name)

            if not success:
                # Clean up any held object first. A stage may have failed while the box was
                # attached; a safe-home with it still attached collides and would burn every
                # retry (the base_link↔box spam we saw). Detach from the planning scene so the
                # home is plannable. No-op if nothing was attached.
                # NOTE (backlog): this only detaches in MoveIt's scene, not LinkAttacher's
                # physics weld — the box stays welded in Gazebo on an abort. Fix recovery later.
                self.moveit2.detach_collision_object(goal.object_id)
                self.moveit2.remove_collision_object(goal.object_id)
                # Force OMPL here too — a stage may have failed while PILZ was the active
                # planner, and PTP-ing home from a low pose could dip through the floor.
                # The safe-home must never inherit PILZ.
                self.moveit2.pipeline_id = 'ompl'
                self.moveit2.planner_id  = 'RRTConnect'
                # max_retries=1: a single safe-home attempt. If the home itself can't plan,
                # retrying the identical request 5x just spams the log — abort cleanly instead.
                self._execute_motion(
                    lambda: self.moveit2.move_to_configuration(
                        joint_positions=[0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0]
                    ), 'HOMING', max_retries=1)
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
        