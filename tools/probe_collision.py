"""
Check that the simulated robot stays on the floor when it is driven into obstacles (ISSUE-016).

Needs a running simulation of the furnished house
(``ros2 launch rosorin_navigation sim.launch.py``).
The robot is reset to the centre of the house and driven at ``--speed`` (default 1.0 m/s, faster
than teleop or Nav2 normally drive) in 8 directions, into walls and furniture; one run also
reverses, turns and strafes while the robot is pinned against an obstacle, the sequence that made
the old VelocityControl drive climb and fly off. The true pose comes from
``/world/robot_world/pose/info``. PASS when roll and pitch stay below ``--max-tilt`` degrees and
the height below ``--max-z`` metres throughout; the exit code is 1 on FAIL.

usage: python3 tools/probe_collision.py [--speed 1.0] [--max-tilt 10] [--max-z 0.05]
"""

import argparse
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

import rclpy
from geometry_msgs.msg import Twist

POSE_TOPIC = '/world/robot_world/pose/info'
SET_POSE = '/world/robot_world/set_pose'


def parse_poses(text):
    """Return [(x, y, z, roll_deg, pitch_deg)] for the model ``rosorin``."""
    out = []
    for m in re.finditer(r'name: "rosorin"\s+id: \d+\s+position \{(.*?)\}\s+orientation \{(.*?)\}',
                         text, re.S):
        p = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', m.group(1))}
        q = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', m.group(2))}
        x, y, z, w = (q.get(k, 0.0) for k in 'xyzw')
        roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
        out.append((p.get('x', 0.0), p.get('y', 0.0), p.get('z', 0.0),
                    math.degrees(roll), math.degrees(pitch)))
    return out


def reset_pose():
    """Put the robot back at the centre of the house, upright."""
    subprocess.run(['ign', 'service', '-s', SET_POSE, '--reqtype', 'ignition.msgs.Pose',
                    '--reptype', 'ignition.msgs.Boolean', '--timeout', '3000', '--req',
                    'name: "rosorin", position {x: 0, y: 0, z: 0.02}, orientation {w: 1}'],
                   capture_output=True, check=False)


def drive(node, pub, steps):
    """Publish each (vx, vy, wz, seconds) step in turn, then stop; return the recorded poses."""
    with tempfile.NamedTemporaryFile('w+', suffix='.txt') as out:
        rec = subprocess.Popen(['ign', 'topic', '-e', '-t', POSE_TOPIC], stdout=out,
                               start_new_session=True)
        time.sleep(1.0)
        for vx, vy, wz, seconds in steps:
            tw = Twist()
            tw.linear.x, tw.linear.y, tw.angular.z = vx, vy, wz
            t_end = time.time() + seconds
            while time.time() < t_end:
                pub.publish(tw)
                rclpy.spin_once(node, timeout_sec=0.05)
        pub.publish(Twist())
        time.sleep(1.0)
        os.killpg(rec.pid, signal.SIGTERM)
        rec.wait()
        out.seek(0)
        return parse_poses(out.read())


def main():
    """Run the collision cases and print one line per case."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--speed', type=float, default=1.0)
    ap.add_argument('--max-tilt', type=float, default=10.0)
    ap.add_argument('--max-z', type=float, default=0.05)
    args = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node('probe_collision')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    time.sleep(1.0)
    v = args.speed
    cases = [('heading %3d' % h, [(v * math.cos(math.radians(h)), v * math.sin(math.radians(h)),
                                   0.0, 7.0)]) for h in range(0, 360, 45)]
    d = v / math.sqrt(2)
    cases.append(('pinned+moves', [(d, -d, 0.0, 6.0), (-v, 0.0, 0.0, 3.0), (d, -d, 0.0, 3.0),
                                   (0.0, 0.0, 1.0, 3.0), (d, -d, 0.0, 3.0), (0.0, v, 0.0, 3.0)]))
    ok = True
    print('%-13s %9s %7s  %s' % ('case', 'max tilt', 'max z', 'result'))
    for name, steps in cases:
        pub.publish(Twist())
        reset_pose()
        time.sleep(1.0)
        poses = drive(node, pub, steps)
        if not poses:
            print('%-13s no pose received' % name)
            ok = False
            continue
        tilt = max(max(abs(p[3]), abs(p[4])) for p in poses)
        z = max(p[2] for p in poses)
        good = tilt < args.max_tilt and z < args.max_z
        ok &= good
        print('%-13s %8.1f° %6.3f  %s' % (name, tilt, z, 'PASS' if good else 'FAIL'))
    reset_pose()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
