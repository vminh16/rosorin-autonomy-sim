#! /usr/bin/env python3
"""
Follow the waypoints of a YAML file with Nav2 and log one CSV row per waypoint.

Based on example_waypoint_follower.py of nav2_simple_commander (Nav2, branch humble,
https://github.com/ros-planning/navigation2/blob/humble/nav2_simple_commander/nav2_simple_commander/example_waypoint_follower.py,
Copyright 2021 Samsung Research America, Apache-2.0). Changes:
  - waypoints come from a YAML file (parameter waypoints_file) instead of hardcoded poses
  - the initial pose is only published when set_initial_pose is true; otherwise the node waits for
    the pose AMCL already has, because waitUntilNav2Active() publishes the map origin when it has
    not received /amcl_pose yet
  - per waypoint: start and end time (sim time), status (SUCCEEDED or FAILED), distance driven
    (integrated from /odom) and the final pose from TF map -> base_footprint, written to
    <output_dir>/<YYYYmmdd-HHMMSS>.csv
  - no preemption demo; a single timeout for the whole route

Run with Nav2 up (navigation.launch.py):
  ros2 run rosorin_navigation waypoint_follower --ros-args \
    -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml
"""

import csv
from datetime import datetime
import math
import os

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry
import rclpy
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from rclpy.time import Time
import tf2_ros
import yaml

CSV_FIELDS = ['run', 'index', 'name', 'goal_x', 'goal_y', 'goal_yaw', 'start_s', 'end_s',
              'duration_s', 'status', 'distance_m', 'final_x', 'final_y', 'final_yaw',
              'error_xy_m', 'error_yaw_deg']


def load_waypoints(path):
    """Return (frame_id, [{name, x, y, yaw}]) from a waypoints YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    points = []
    for i, w in enumerate(data['waypoints']):
        points.append({'name': str(w.get('name', 'wp%d' % i)), 'x': float(w['x']),
                       'y': float(w['y']), 'yaw': float(w.get('yaw', 0.0))})
    return data.get('frame_id', 'map'), points


def make_pose(navigator, frame_id, x, y, yaw):
    """Build a PoseStamped from x, y, yaw."""
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def yaw_of(q):
    """Yaw angle of a quaternion."""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angle_diff(a, b):
    """Return a - b wrapped to [-pi, pi]."""
    return math.atan2(math.sin(a - b), math.cos(a - b))


class Odometer:
    """Distance driven, integrated from /odom."""

    def __init__(self, node):
        self.total = 0.0
        self._last = None
        node.create_subscription(Odometry, 'odom', self._callback, 20)

    def _callback(self, msg):
        p = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        if self._last is not None:
            self.total += math.hypot(p[0] - self._last[0], p[1] - self._last[1])
        self._last = p


def main():
    rclpy.init()
    navigator = BasicNavigator(node_name='rosorin_waypoint_follower')
    # this package drives the simulation, where every node runs on the Gazebo clock
    navigator.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
    default_file = os.path.join(get_package_share_directory('rosorin_navigation'),
                                'config', 'waypoints.yaml')
    waypoints_file = navigator.declare_parameter('waypoints_file', default_file).value
    output_dir = navigator.declare_parameter('output_dir', 'results/nav_runs').value
    timeout_s = navigator.declare_parameter('timeout', 900.0).value
    set_initial = navigator.declare_parameter('set_initial_pose', False).value
    initial = [navigator.declare_parameter(n, 0.0).value
               for n in ('initial_x', 'initial_y', 'initial_yaw')]

    frame_id, waypoints = load_waypoints(waypoints_file)
    navigator.info('Loaded %d waypoints from %s' % (len(waypoints), waypoints_file))
    odometer = Odometer(navigator)
    tf_buffer = tf2_ros.Buffer()
    tf2_ros.TransformListener(tf_buffer, navigator)

    if set_initial:
        navigator.setInitialPose(make_pose(navigator, 'map', *initial))
    else:
        navigator.info('Waiting for the current AMCL pose (set_initial_pose is false)')
        while rclpy.ok() and not navigator.initial_pose_received:
            rclpy.spin_once(navigator, timeout_sec=0.5)
    navigator.waitUntilNav2Active()

    def robot_pose():
        try:
            t = tf_buffer.lookup_transform(frame_id, 'base_footprint', Time()).transform
            return t.translation.x, t.translation.y, yaw_of(t.rotation)
        except tf2_ros.TransformException:
            return float('nan'), float('nan'), float('nan')

    def now_s():
        return navigator.get_clock().now().nanoseconds / 1e9

    run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
    poses = [make_pose(navigator, frame_id, w['x'], w['y'], w['yaw']) for w in waypoints]
    segments = {}  # index -> (start_s, start_dist, end_s, end_dist, final pose)
    current, seg_start, seg_dist = 0, now_s(), odometer.total

    def close_segment(index):
        nonlocal seg_start, seg_dist
        segments[index] = (seg_start, seg_dist, now_s(), odometer.total, robot_pose())
        seg_start, seg_dist = now_s(), odometer.total

    nav_start = navigator.get_clock().now()
    if not navigator.followWaypoints(poses):
        rclpy.shutdown()
        return 1
    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback and feedback.current_waypoint > current:
            # the follower moved on: earlier waypoints are done (status comes with the result)
            for i in range(current, min(feedback.current_waypoint, len(waypoints))):
                close_segment(i)
            current = feedback.current_waypoint
        if navigator.get_clock().now() - nav_start > Duration(seconds=timeout_s):
            navigator.warn('Route timeout (%.0f s), cancelling' % timeout_s)
            navigator.cancelTask()
    result = navigator.getResult()
    if current < len(waypoints):
        close_segment(current)
    missed = set(navigator.result_future.result().result.missed_waypoints)

    rows = []
    for i, w in enumerate(waypoints):
        start_s, start_dist, end_s, end_dist, (x, y, yaw) = segments.get(
            i, (now_s(), 0.0, now_s(), 0.0, (float('nan'),) * 3))
        reached = i not in missed and (
            i < current or (i == current and result == TaskResult.SUCCEEDED))
        rows.append({
            'run': run_id, 'index': i, 'name': w['name'], 'goal_x': w['x'], 'goal_y': w['y'],
            'goal_yaw': w['yaw'], 'start_s': '%.2f' % start_s, 'end_s': '%.2f' % end_s,
            'duration_s': '%.2f' % (end_s - start_s),
            'status': 'SUCCEEDED' if reached else 'FAILED',
            'distance_m': '%.3f' % (end_dist - start_dist), 'final_x': '%.3f' % x,
            'final_y': '%.3f' % y, 'final_yaw': '%.3f' % yaw,
            'error_xy_m': '%.3f' % math.hypot(x - w['x'], y - w['y']),
            'error_yaw_deg': '%.1f' % math.degrees(angle_diff(yaw, w['yaw']))})
        navigator.info('Waypoint %d/%d %s: %s, %s s, %s m, error %s m' % (
            i + 1, len(waypoints), w['name'], rows[-1]['status'], rows[-1]['duration_s'],
            rows[-1]['distance_m'], rows[-1]['error_xy_m']))

    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, run_id + '.csv')
    with open(out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    n_reached = sum(r['status'] == 'SUCCEEDED' for r in rows)
    navigator.info('Route %s: %d/%d waypoints reached, log %s' % (
        {TaskResult.SUCCEEDED: 'SUCCEEDED', TaskResult.FAILED: 'FAILED',
         TaskResult.CANCELED: 'CANCELED'}.get(result, 'UNKNOWN'),
        n_reached, len(waypoints), out))
    navigator.destroy_node()
    rclpy.shutdown()
    return 0 if n_reached == len(waypoints) else 1


if __name__ == '__main__':
    raise SystemExit(main())
