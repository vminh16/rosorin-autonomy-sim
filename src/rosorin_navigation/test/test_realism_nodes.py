"""Unit tests of the realism:=true nodes (no simulator needed)."""

import math

import numpy as np
from rosorin_navigation.scan_noise import noisy_ranges
from rosorin_navigation.wheel_odometry import body_motion

R, L = 0.04, 0.174355


def wheel_angles(vx, vy, wz):
    """Wheel speeds of the simulated MecanumDrive (signs measured in Gazebo), rad/s."""
    return ((vx - vy - L * wz) / R, (vx + vy + L * wz) / R,
            (vx + vy - L * wz) / R, (vx - vy + L * wz) / R)


def test_kinematics_round_trip():
    """body_motion inverts the wheel speeds Gazebo produces for each motion."""
    for twist in ((0.2, 0.0, 0.0), (0.0, 0.2, 0.0), (0.0, 0.0, 0.5), (0.1, -0.05, 0.3)):
        assert np.allclose(body_motion(*wheel_angles(*twist), R, L), twist)


def test_measured_wheel_speeds():
    """Speeds measured in the simulation: 0.2 m/s -> 5 rad/s, 0.5 rad/s -> 2.18 rad/s."""
    assert np.allclose(wheel_angles(0.2, 0.0, 0.0), (5.0, 5.0, 5.0, 5.0))
    assert np.allclose(wheel_angles(0.0, 0.2, 0.0), (-5.0, 5.0, 5.0, -5.0))
    assert np.allclose(wheel_angles(0.0, 0.0, 0.5), (-2.18, 2.18, -2.18, 2.18), atol=0.01)


def test_scan_noise_by_range():
    """Noise sigma follows the COIN-D6 bands and inf stays inf."""
    rng = np.random.default_rng(1)
    near = np.full(20000, 1.0)
    far = np.full(20000, 5.0)
    assert math.isclose(np.std(noisy_ranges(near, 0.002, 0.0075, 2.0, rng) - near), 0.002,
                        rel_tol=0.05)
    assert math.isclose(np.std(noisy_ranges(far, 0.002, 0.0075, 2.0, rng) - far), 0.0075,
                        rel_tol=0.05)
    out = noisy_ranges([math.inf, 1.0], 0.002, 0.0075, 2.0, rng)
    assert math.isinf(out[0])
