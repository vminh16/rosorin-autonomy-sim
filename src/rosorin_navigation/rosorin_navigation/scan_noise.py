#! /usr/bin/env python3
"""
Add the range-dependent noise of the COIN-D6 LiDAR to the simulated scan.

The wiki (1.10.5) gives the accuracy as <= 4 mm for 0.1 - 2 m and <= 15 mm for 2 - 12 m. Gazebo
can only add one fixed standard deviation, so with realism:=true the sensor runs without noise, its
scan is bridged as /scan_raw and this node publishes /scan with a Gaussian error of half the stated
bound (the bound taken as 2 sigma): 2 mm below 2 m, 7.5 mm above. Ranges outside the sensor limits
are left untouched (inf stays inf).

Started by sim.launch.py realism:=true.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def noisy_ranges(ranges, near_sigma, far_sigma, split, rng):
    """Return ranges with Gaussian noise whose sigma depends on the distance."""
    r = np.asarray(ranges, dtype=np.float32)
    valid = np.isfinite(r)
    sigma = np.where(r < split, near_sigma, far_sigma)
    noise = rng.normal(0.0, 1.0, r.shape).astype(np.float32) * sigma
    return np.where(valid, r + noise, r)


class ScanNoise(Node):
    """Republish /scan_raw as /scan with COIN-D6 range noise."""

    def __init__(self):
        super().__init__('scan_noise')
        self.near_sigma = self.declare_parameter('near_sigma', 0.002).value
        self.far_sigma = self.declare_parameter('far_sigma', 0.0075).value
        self.split = self.declare_parameter('split_range', 2.0).value
        self.rng = np.random.default_rng(self.declare_parameter('seed', 0).value or None)
        # reliable, as the bridge published /scan before: SLAM, AMCL and costmaps all accept it
        self.pub = self.create_publisher(LaserScan, 'scan', 10)
        self.create_subscription(LaserScan, 'scan_raw', self.on_scan, qos_profile_sensor_data)

    def on_scan(self, msg):
        r = noisy_ranges(msg.ranges, self.near_sigma, self.far_sigma, self.split, self.rng)
        msg.ranges = np.clip(r, msg.range_min, None).tolist()
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ScanNoise()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
