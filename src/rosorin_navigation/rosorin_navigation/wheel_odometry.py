#! /usr/bin/env python3
"""
Wheel odometry of the ROSOrin Pro from the simulated wheel encoders, published as /odom_raw.

The real robot computes odometry from its four encoders and the mecanum kinematics (wiki 2.1.4,
node odom_publisher, 50 Hz, frame odom -> base_footprint) and fuses it with the IMU in
robot_localization; the fused result is /odom. This node plays odom_publisher in the simulation,
so that /odom drifts as on the robot instead of being the true pose from Gazebo:
  - wheel angles from /joint_states, rounded to the encoder resolution: 11 lines x 4 (quadrature)
    x 90 (gear ratio) = 3960 counts per wheel turn (wiki 1.10.2.3; the x4 decoding is assumed)
  - forward kinematics with the wiki constants: wheel radius 0.04 m, lever arm
    (wheelbase + track) / 2 = 0.174355 m; wheel signs measured in the simulation
    (vx: + + + +, vy: - + + -, wz: - + - +)
  - calibration residuals as scale errors: forward +2 % and rotation +0.4 % are inside the
    tolerances of the wiki calibration (3 cm over 1 m, 1.5 degrees over 360 degrees, 2.1.2 and
    2.1.3); sideways -4 % (mecanum rollers slip more when strafing and the robot does not
    calibrate it: an assumption)
  - 1 % random slip per wheel and step
  - the covariances of the real odom_publisher (moving and stopped, wiki 2.1.4 Global
    Parameters): yaw is 1e3 while moving, so the EKF takes the heading rate from the IMU. The
    stopped covariances are used only once the wheels have been still for stop_delay (0.3 s): in
    the simulation the wheels stop at once while the body coasts for the 0.1 s time constant of
    the drive, and the tight stopped yaw covariance made the EKF lose that rotation (about 1 degree
    per 90 degree turn); on the robot wheels and body stop together

Started by sim.launch.py realism:=true.
"""

import math

import numpy as np
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState

WHEELS = ('front_left_joint', 'front_right_joint', 'rear_left_joint', 'rear_right_joint')

# wiki 2.1.4: ODOM_POSE_COVARIANCE / ODOM_TWIST_COVARIANCE (6x6, row major)
COV_MOVING = [0.0] * 36
for _i, _v in zip((0, 7, 14, 21, 28, 35), (1e-3, 1e-3, 1e6, 1e6, 1e6, 1e3)):
    COV_MOVING[_i] = _v
COV_STOPPED = [0.0] * 36
for _i, _v in zip((0, 7, 8, 14, 21, 28, 35), (1e-9, 1e-3, 1e-9, 1e6, 1e6, 1e6, 1e-9)):
    COV_STOPPED[_i] = _v


def body_motion(d_fl, d_fr, d_rl, d_rr, radius, lever):
    """Return dx, dy, dyaw of the body for the wheel angle increments (mecanum, X layout)."""
    dx = radius / 4.0 * (d_fl + d_fr + d_rl + d_rr)
    dy = radius / 4.0 * (-d_fl + d_fr + d_rl - d_rr)
    dyaw = radius / (4.0 * lever) * (-d_fl + d_fr - d_rl + d_rr)
    return dx, dy, dyaw


def yaw_to_quaternion(yaw):
    """Return the quaternion of a rotation about z."""
    return Quaternion(z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))


class WheelOdometry(Node):
    """Integrate encoder ticks into /odom_raw with calibration errors and slip."""

    def __init__(self):
        super().__init__('wheel_odometry')
        p = self.declare_parameter
        self.radius = p('wheel_radius', 0.04).value
        self.lever = p('lever_arm', 0.174355).value
        self.tick = 2.0 * math.pi / p('counts_per_rev', 3960).value
        self.scale = (1.0 + p('forward_scale_error', 0.02).value,
                      1.0 + p('sideways_scale_error', -0.04).value,
                      1.0 + p('rotation_scale_error', 0.004).value)
        self.slip = p('slip_stddev', 0.01).value
        self.period = 1.0 / p('rate', 50.0).value
        self.stop_delay = p('stop_delay', 0.3).value
        self.last_motion = None
        self.frame = p('odom_frame', 'odom').value
        self.child = p('base_frame', 'base_footprint').value
        self.rng = np.random.default_rng(p('seed', 0).value or None)
        self.pub = self.create_publisher(Odometry, 'odom_raw', 10)
        self.create_subscription(JointState, 'joint_states', self.on_joints, 10)
        self.last_ticks = None
        self.last_pub = None
        self.x = self.y = self.yaw = 0.0
        self.acc = [0.0, 0.0, 0.0]   # body motion since the last message

    def on_joints(self, msg):
        pos = dict(zip(msg.name, msg.position))
        if not all(w in pos for w in WHEELS):
            return
        ticks = [math.floor(pos[w] / self.tick) for w in WHEELS]
        stamp = Time.from_msg(msg.header.stamp)
        if self.last_ticks is None:
            self.last_ticks, self.last_pub = ticks, stamp
            return
        d = [(t - t0) * self.tick * (1.0 + self.rng.normal(0.0, self.slip))
             for t, t0 in zip(ticks, self.last_ticks)]
        self.last_ticks = ticks
        dx, dy, dyaw = body_motion(*d, self.radius, self.lever)
        dx, dy, dyaw = dx * self.scale[0], dy * self.scale[1], dyaw * self.scale[2]
        mid = self.yaw + dyaw / 2.0
        self.x += dx * math.cos(mid) - dy * math.sin(mid)
        self.y += dx * math.sin(mid) + dy * math.cos(mid)
        self.yaw = math.atan2(math.sin(self.yaw + dyaw), math.cos(self.yaw + dyaw))
        self.acc = [a + b for a, b in zip(self.acc, (dx, dy, dyaw))]
        dt = (stamp - self.last_pub).nanoseconds * 1e-9
        if dt >= self.period:
            self.publish(msg.header.stamp, dt)
            self.acc, self.last_pub = [0.0, 0.0, 0.0], stamp

    def publish(self, stamp, dt):
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id, odom.child_frame_id = self.frame, self.child
        odom.pose.pose.position.x, odom.pose.pose.position.y = self.x, self.y
        odom.pose.pose.orientation = yaw_to_quaternion(self.yaw)
        odom.twist.twist.linear.x = self.acc[0] / dt
        odom.twist.twist.linear.y = self.acc[1] / dt
        odom.twist.twist.angular.z = self.acc[2] / dt
        now = Time.from_msg(stamp)
        if any(abs(v) > 1e-4 for v in self.acc) or self.last_motion is None:
            self.last_motion = now
        still = (now - self.last_motion).nanoseconds * 1e-9 >= self.stop_delay
        cov = COV_STOPPED if still else COV_MOVING
        odom.pose.covariance, odom.twist.covariance = cov, cov
        self.pub.publish(odom)


def main():
    rclpy.init()
    node = WheelOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
