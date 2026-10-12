"""
Compare commanded and achieved velocity of the simulated robot (ground truth from Gazebo).

Needs a running simulation (``ros2 launch rosorin_navigation sim.launch.py world:=empty``).
For each command (forward, sideways, turn) it publishes ``/cmd_vel`` for a few seconds, records
the true model pose from ``/world/robot_world/pose/info`` and prints the achieved body-frame
velocity and the ratio achieved / commanded (1.00 = the robot moves exactly as commanded).

usage: python3 tools/probe_motion.py [--speed 0.2] [--turn 0.5] [--seconds 4]
"""

import argparse
import math
import os
import re
import signal
import subprocess
import tempfile
import time

import rclpy
from geometry_msgs.msg import Twist

POSE_TOPIC = '/world/robot_world/pose/info'


def parse_poses(text):
    """Return [(sim_time, x, y, yaw)] for the model ``rosorin`` from ``ign topic -e`` output."""
    out = []
    for msg in text.split('\nheader {')[1:]:
        sec = re.search(r'sec: (\d+)\s+nsec: (\d+)', msg)
        pose = re.search(r'name: "rosorin"\s+id: \d+\s+position \{(.*?)\}\s+orientation \{(.*?)\}',
                         msg, re.S)
        if not sec or not pose:
            continue
        p = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', pose.group(1))}
        q = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', pose.group(2))}
        yaw = 2 * math.atan2(q.get('z', 0.0), q.get('w', 1.0))
        out.append((int(sec.group(1)) + int(sec.group(2)) * 1e-9,
                    p.get('x', 0.0), p.get('y', 0.0), yaw))
    return out


def run_command(node, pub, twist, seconds):
    """Publish ``twist`` for ``seconds`` wall seconds, then stop; return the recorded poses."""
    with tempfile.NamedTemporaryFile('w+', suffix='.txt') as out:
        rec = subprocess.Popen(['ign', 'topic', '-e', '-t', POSE_TOPIC], stdout=out,
                               start_new_session=True)
        time.sleep(1.0)
        t_end = time.time() + seconds
        while time.time() < t_end:
            pub.publish(twist)
            rclpy.spin_once(node, timeout_sec=0.05)
        pub.publish(Twist())
        time.sleep(1.5)
        os.killpg(rec.pid, signal.SIGTERM)
        rec.wait()
        out.seek(0)
        return parse_poses(out.read())


def segment_velocities(poses, seg=0.5):
    """Return [(vx, vy, wz)] in the body frame for consecutive ``seg``-second pieces."""
    out = []
    t = poses[0][0]
    while t + seg <= poses[-1][0]:
        win = [p for p in poses if t <= p[0] < t + seg]
        if len(win) >= 2:
            a, b = win[0], win[-1]
            dt = b[0] - a[0]
            dx, dy = b[1] - a[1], b[2] - a[2]
            dyaw = math.atan2(math.sin(b[3] - a[3]), math.cos(b[3] - a[3]))
            c, s = math.cos(a[3]), math.sin(a[3])
            out.append(((c * dx + s * dy) / dt, (-s * dx + c * dy) / dt, dyaw / dt))
        t += seg
    return out


def steady_velocity(poses, axis, commanded):
    """Return the median achieved velocity on ``axis`` over the fastest part of the motion."""
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    vals = [v[idx] for v in segment_velocities(poses)]
    peak = max(abs(v) for v in vals)
    if peak < 1e-3:
        return 0.0
    steady = sorted(v for v in vals if abs(v) > 0.6 * peak and v * commanded > 0)
    return steady[len(steady) // 2] if steady else 0.0


def main():
    """Run the three probes and print a table."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--speed', type=float, default=0.2)
    ap.add_argument('--turn', type=float, default=0.5)
    ap.add_argument('--seconds', type=float, default=4.0)
    args = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node('probe_motion')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    time.sleep(1.0)
    cases = [('forward', Twist(), 'x', args.speed), ('sideways', Twist(), 'y', args.speed),
             ('turn', Twist(), 'z', args.turn)]
    print('%-9s %10s %10s %7s' % ('motion', 'commanded', 'achieved', 'ratio'))
    for name, tw, axis, value in cases:
        if axis == 'z':
            tw.angular.z = value
        else:
            setattr(tw.linear, axis, value)
        poses = run_command(node, pub, tw, args.seconds)
        got = steady_velocity(poses, axis, value)
        print('%-9s %10.3f %10.3f %7.2f' % (name, value, got, got / value))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
