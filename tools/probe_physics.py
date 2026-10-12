"""
Check the physical behaviour of the simulated robot against the real ROSOrin Pro.

Needs a running simulation (``ros2 launch rosorin_navigation sim.launch.py world:=empty``)
and nothing else loading the machine. Ground truth: ``/world/robot_world/pose/info`` (sim time).
Reference values (Hiwonder wiki): wheel diameter 0.08 m and lever arm 0.174355 m (2.2.2.4),
motor no-load speed 110 rpm at the output shaft (1.10.2.3), so a wheel cannot exceed
0.461 m/s; drive force capped by traction mu*g (PlanarDrive, mu 0.6). Cases:

- rest:      no command for 10 s: the body must not creep, sink or tilt
- imu:       at rest /imu reads gravity (+9.8 m/s2 on z) and no rotation
- step:      0 -> 0.3 m/s: 63 % of the speed within 0.25 s, acceleration not above mu*g
- top speed: commands beyond the motor limit saturate at the wheel limit (vx, vy, wz)
- stop:      after a stop command the speed falls below 0.01 m/s within 0.5 s

usage: python3 tools/probe_physics.py        (exit code 1 if a case fails)
"""

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
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

POSE_TOPIC = '/world/robot_world/pose/info'
WHEEL_RADIUS = 0.04
LEVER_ARM = 0.174355
MAX_WHEEL = 110 * 2 * math.pi / 60          # rad/s, motor no-load speed
V_MAX = MAX_WHEEL * WHEEL_RADIUS            # 0.461 m/s
W_MAX = V_MAX / LEVER_ARM                   # 2.64 rad/s
MU_G = 0.6 * 9.8


def parse(text):
    """Return [(t, x, y, z, roll, pitch, yaw)] of the model ``rosorin``."""
    out = []
    for msg in text.split('\nheader {')[1:]:
        st = re.search(r'sec: (\d+)\s+nsec: (\d+)', msg)
        m = re.search(r'name: "rosorin"\s+id: \d+\s+position \{(.*?)\}\s+orientation \{(.*?)\}',
                      msg, re.S)
        if not st or not m:
            continue
        p = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', m.group(1))}
        q = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e+]+)', m.group(2))}
        x, y, z, w = (q.get(k, 0.0) for k in 'xyzw')
        out.append((int(st.group(1)) + int(st.group(2)) * 1e-9, p.get('x', 0.0), p.get('y', 0.0),
                    p.get('z', 0.0), math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)),
                    math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))),
                    math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))))
    return out


class Probe:
    """Publish commands, record poses and IMU."""

    def __init__(self):
        rclpy.init()
        self.node = rclpy.create_node('probe_physics')
        self.pub = self.node.create_publisher(Twist, '/cmd_vel', 10)
        self.imu = []
        self.node.create_subscription(Imu, '/imu', self.imu.append, qos_profile_sensor_data)
        time.sleep(1.0)

    def run(self, steps):
        """Publish each (vx, vy, wz, seconds) step; return poses and IMU messages recorded."""
        self.imu.clear()
        with tempfile.NamedTemporaryFile('w+', suffix='.txt') as out:
            rec = subprocess.Popen(['ign', 'topic', '-e', '-t', POSE_TOPIC], stdout=out,
                                   start_new_session=True)
            time.sleep(1.0)
            for vx, vy, wz, seconds in steps:
                tw = Twist()
                tw.linear.x, tw.linear.y, tw.angular.z = vx, vy, wz
                t_end = time.time() + seconds
                while time.time() < t_end:
                    self.pub.publish(tw)
                    rclpy.spin_once(self.node, timeout_sec=0.05)
            os.killpg(rec.pid, signal.SIGTERM)
            rec.wait()
            out.seek(0)
            return parse(out.read()), list(self.imu)


def body_speed(poses, dt=0.1):
    """Return [(t, vx_body, vy_body, wz)] from poses ``dt`` seconds apart."""
    out = []
    j = 0
    for i, a in enumerate(poses):
        while j < len(poses) and poses[j][0] < a[0] + dt:
            j += 1
        if j >= len(poses):
            break
        b = poses[j]
        h = b[0] - a[0]
        dx, dy = b[1] - a[1], b[2] - a[2]
        c, s = math.cos(a[6]), math.sin(a[6])
        dyaw = math.atan2(math.sin(b[6] - a[6]), math.cos(b[6] - a[6]))
        out.append((a[0], (c * dx + s * dy) / h, (-s * dx + c * dy) / h, dyaw / h))
    return out


def report(name, ok, detail):
    """Print one result line and return ``ok``."""
    print('%-10s %-4s %s' % (name, 'PASS' if ok else 'FAIL', detail))
    return ok


def main():
    """Run all cases."""
    p = Probe()
    ok = True
    p.run([(0.0, 0.0, 0.0, 2.0)])                        # settle

    poses, imu = p.run([(0.0, 0.0, 0.0, 10.0)])
    drift = math.hypot(poses[-1][1] - poses[0][1], poses[-1][2] - poses[0][2])
    dz = max(abs(q[3] - poses[0][3]) for q in poses)
    tilt = max(max(abs(q[4]), abs(q[5])) for q in poses)
    ok &= report('rest', drift < 0.002 and dz < 0.002 and math.degrees(tilt) < 0.5,
                 'xy creep %.4f m, z change %.4f m, tilt %.2f deg over %.1f s' % (
                     drift, dz, math.degrees(tilt), poses[-1][0] - poses[0][0]))

    n = max(len(imu), 1)
    acc = [sum(getattr(m.linear_acceleration, k) for m in imu) / n for k in 'xyz']
    gyr = [sum(getattr(m.angular_velocity, k) for m in imu) / n for k in 'xyz']
    ok &= report('imu', len(imu) > 100 and abs(acc[2] - 9.8) < 0.1
                 and max(map(abs, acc[:2])) < 0.1 and max(map(abs, gyr)) < 0.01,
                 '%d msgs, accel (%.3f, %.3f, %.3f) m/s2, gyro (%.4f, %.4f, %.4f) rad/s' % (
                     len(imu), *acc, *gyr))

    poses, _ = p.run([(0.3, 0.0, 0.0, 3.0), (0.0, 0.0, 0.0, 2.0)])
    v = body_speed(poses, dt=0.02)
    t_cmd = next(t for t, vx, _, _ in v if vx > 0.003)
    t63 = next(t for t, vx, _, _ in v if vx >= 0.63 * 0.3) - t_cmd
    vs = body_speed(poses, dt=0.05)
    acc_max = max(abs(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(vs, vs[5:]) if b[0] > a[0])
    ok &= report('step', 0.0 < t63 <= 0.25 and acc_max <= MU_G * 1.1,
                 '0 -> 0.3 m/s: 63%% after %.3f s, max acceleration %.2f m/s2 '
                 '(limit mu*g %.2f)' % (t63, acc_max, MU_G))
    t_stop = max(t for t, vx, _, _ in v if vx > 0.25)
    t_zero = next(t for t, vx, _, _ in v if t > t_stop and abs(vx) < 0.01) - t_stop
    ok &= report('stop', t_zero <= 0.5, 'below 0.01 m/s %.3f s after leaving cruise' % t_zero)

    for name, cmd, idx, limit in (('top vx', (1.0, 0.0, 0.0), 1, V_MAX),
                                  ('top vy', (0.0, 1.0, 0.0), 2, V_MAX),
                                  ('top wz', (0.0, 0.0, 5.0), 3, W_MAX)):
        p.run([(0.0, 0.0, 0.0, 1.0)])
        poses, _ = p.run([(*cmd, 4.0)])
        vals = sorted(abs(s[idx]) for s in body_speed(poses, dt=0.5))
        steady = vals[int(len(vals) * 0.8)]
        ok &= report(name, abs(steady - limit) <= 0.03 * limit,
                     'command %.1f -> steady %.3f (wheel-speed limit %.3f)' % (
                         max(cmd), steady, limit))
    p.run([(0.0, 0.0, 0.0, 1.0)])
    p.node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
