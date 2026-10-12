"""
Check that the simulated ROSOrin Pro reproduces the real robot described in the Hiwonder wiki.

Run from the repository root after sourcing the workspace::

    python3 -m pytest src/rosorin_navigation/test/test_sim_fidelity.py -q

Reference values live in ``config/wiki_reference.yaml``; each test compares one aspect of the
URDF that ``sim.launch.py`` loads against it.
"""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(__file__))

import sim_inspect as si  # noqa: E402

REFERENCE = os.path.join(si.PKG_ROOT, 'config', 'wiki_reference.yaml')


@pytest.fixture(scope='module')
def ref():
    """Return the wiki reference values."""
    with open(REFERENCE) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope='module')
def robot():
    """Return the URDF of the simulated robot."""
    return si.load_robot()


def _near(value, expected, rel=None, abs_=None):
    """Return True if ``value`` is within a relative or absolute tolerance of ``expected``."""
    if abs_ is not None:
        return abs(value - expected) <= abs_
    return abs(value - expected) <= rel * abs(expected)


def test_lidar_field_of_view(robot, ref):
    """The COIN-D6 scans a full 360 degrees."""
    lid = si.lidar(robot)
    assert _near(lid['fov_deg'], ref['lidar']['fov_deg'], abs_=2.0), lid['fov_deg']


def test_lidar_angular_resolution(robot, ref):
    """The COIN-D6 has 0.9 degrees resolution (400 samples per turn)."""
    lid = si.lidar(robot)
    assert _near(lid['resolution_deg'], ref['lidar']['resolution_deg'], abs_=0.1), \
        lid['resolution_deg']


def test_lidar_rate_and_range(robot, ref):
    """The COIN-D6 spins at 10 Hz and reaches 12 m."""
    lid = si.lidar(robot)
    assert _near(lid['rate_hz'], ref['lidar']['rate_hz'], ref['lidar']['tol'])
    assert _near(lid['range_max'], ref['lidar']['range_max'], ref['lidar']['tol'])
    assert _near(lid['range_min'], ref['lidar']['range_min'],
                 abs_=ref['lidar']['range_min_tol_abs'])


def test_camera_resolution_and_rate(robot, ref):
    """The Aurora930 streams 640x400 at 12 fps."""
    cams = si.cameras(robot)
    assert cams, 'no camera sensor in the URDF'
    cam = cams[0]
    assert (cam['width'], cam['height']) == (ref['camera']['width'], ref['camera']['height'])
    assert _near(cam['rate_hz'], ref['camera']['rate_hz'], ref['camera']['tol']), cam['rate_hz']


def test_camera_field_of_view(robot, ref):
    """The Aurora930 horizontal FOV is 71 to 74 degrees."""
    cam = si.cameras(robot)[0]
    assert _near(cam['hfov_deg'], ref['camera']['hfov_deg'], abs_=ref['camera']['hfov_tol_abs']), \
        cam['hfov_deg']


def test_imu_present(robot, ref):
    """The robot publishes IMU data."""
    assert si.has_imu(robot) is ref['imu']['present']


def test_drive_wheel_radius(robot, ref):
    """The drive plugin uses the real wheel radius (0.08 m diameter)."""
    plugin = si.mecanum_plugin(robot)
    assert _near(plugin['wheel_radius'], ref['drive']['wheel_radius'], ref['drive']['tol']), \
        plugin['wheel_radius']


def test_drive_lever_arm(robot, ref):
    """The drive plugin uses the real kinematic lever arm (wheelbase + track) / 2."""
    plugin = si.mecanum_plugin(robot)
    lever = (plugin['wheel_separation'] + plugin['wheelbase']) / 2
    assert _near(lever, ref['drive']['lever_arm'], ref['drive']['tol']), lever


def test_plugin_matches_wheel_geometry(robot):
    """The drive plugin parameters agree with the wheels that are actually simulated."""
    plugin = si.mecanum_plugin(robot)
    wheels = si.driven_wheels(robot)
    assert _near(plugin['wheel_radius'], wheels['radius'], 0.02), (plugin, wheels)
    lever_plugin = (plugin['wheel_separation'] + plugin['wheelbase']) / 2
    lever_wheels = (wheels['track'] + wheels['wheelbase']) / 2
    assert _near(lever_plugin, lever_wheels, 0.05), (lever_plugin, lever_wheels)


def _plugins(robot):
    """Return the Gazebo plugins declared in the URDF."""
    return list(robot.iter('plugin'))


def test_drive_force_is_traction_limited(robot, ref):
    """The body is driven by force-limited PlanarDrive, not by velocity override (ISSUE-016)."""
    names = [p.get('name', '') for p in _plugins(robot)]
    assert not any(n.endswith('VelocityControl') for n in names), names
    drive = next(p for p in _plugins(robot) if p.get('name') == 'rosorin::PlanarDrive')
    assert 0.3 <= float(drive.findtext('traction_coefficient')) <= 1.0
    lever = float(drive.findtext('lever_arm'))
    assert _near(lever, ref['drive']['lever_arm'], ref['drive']['tol']), lever


def test_single_odom_publisher(robot):
    """Only one plugin publishes /odom (MecanumDrive wheel odometry used to interleave)."""
    odom = [p.get('name') for p in _plugins(robot)
            if (p.findtext('odom_topic') or '').strip() == '/odom']
    assert len(odom) == 1, odom


def test_total_mass_is_plausible(robot, ref):
    """The total mass is in the range of a 3 kg desktop robot, not 40 kg."""
    mass = si.total_mass(robot)
    assert ref['body']['total_mass_min'] <= mass <= ref['body']['total_mass_max'], mass
