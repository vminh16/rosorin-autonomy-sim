"""Scripted driving for the demo: forward/back, left/right (mecanum), a full turn; ends where it started."""
import time
import rclpy
from geometry_msgs.msg import Twist
rclpy.init(); n = rclpy.create_node('demo_drive')
pub = n.create_publisher(Twist, '/cmd_vel', 10)
def move(label, vx, vy, wz, sec):
    print(f'{label:<22} vx={vx:+.2f} m/s  vy={vy:+.2f} m/s  wz={wz:+.2f} rad/s  for {sec:.1f} s', flush=True)
    t = Twist(); t.linear.x, t.linear.y, t.angular.z = float(vx), float(vy), float(wz)
    end = time.time() + sec
    while time.time() < end:
        pub.publish(t); time.sleep(0.05)
    pub.publish(Twist()); time.sleep(0.8)
time.sleep(1.0)
move('forward', 0.25, 0, 0, 2.4)
move('backward', -0.25, 0, 0, 2.4)
move('sideways left', 0, 0.25, 0, 2.0)
move('sideways right', 0, -0.25, 0, 2.0)
move('turn on the spot', 0, 0, 0.8, 7.854)
print('done: back at the start pose', flush=True)
