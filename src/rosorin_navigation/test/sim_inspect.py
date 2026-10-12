"""
Read the physical and sensor parameters of the simulated ROSOrin Pro from its URDF.

Used by ``test_sim_fidelity.py`` to compare the simulation against the values
published in the Hiwonder wiki (``config/wiki_reference.yaml``).
"""

import math
import os
import subprocess
import xml.etree.ElementTree as ET

PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPSTREAM_XACRO = os.path.join(
    PKG_ROOT, '..', 'simulations', 'robot_gazebo', 'urdf', 'robot.gazebo.xacro')
OWN_XACRO = os.path.join(PKG_ROOT, 'urdf', 'rosorin_sim.urdf.xacro')


def sim_xacro_path():
    """Return the xacro ``sim.launch.py`` loads: our fixed copy if it exists, else upstream."""
    return OWN_XACRO if os.path.exists(OWN_XACRO) else os.path.normpath(UPSTREAM_XACRO)


def load_robot(xacro_file=None):
    """Expand the xacro and return the parsed URDF root element."""
    env = dict(os.environ)
    env.setdefault('DEPTH_CAMERA_TYPE', 'aurora')
    out = subprocess.run(
        ['xacro', xacro_file or sim_xacro_path(), 'sim_ign:=true'],
        check=True, capture_output=True, text=True, env=env).stdout
    return ET.fromstring(out)


def _f(node, path, default=None):
    """Return the float value of a child element, or ``default``."""
    el = node.find(path)
    return float(el.text) if el is not None and el.text else default


def _xyz(origin):
    """Return (x, y, z) of a URDF ``<origin>`` element."""
    if origin is None:
        return (0.0, 0.0, 0.0)
    return tuple(float(v) for v in origin.get('xyz', '0 0 0').split())


def sensors(robot):
    """Return every Gazebo ``<sensor>`` as a dict (type, name, link, parameters)."""
    found = []
    for gz in robot.iter('gazebo'):
        for s in gz.findall('sensor'):
            found.append({'type': s.get('type'), 'name': s.get('name'),
                          'link': gz.get('reference'), 'el': s})
    return found


def lidar(robot):
    """Return the LiDAR parameters (angles in degrees)."""
    for s in sensors(robot):
        if s['type'] in ('gpu_lidar', 'lidar'):
            el = s['el']
            h = el.find('ray/scan/horizontal')
            lo, hi = _f(h, 'min_angle'), _f(h, 'max_angle')
            n = int(_f(h, 'samples'))
            return {
                'fov_deg': math.degrees(hi - lo),
                'samples': n,
                'resolution_deg': math.degrees(hi - lo) / max(n - 1, 1),
                'range_min': _f(el, 'ray/range/min'),
                'range_max': _f(el, 'ray/range/max'),
                'rate_hz': _f(el, 'update_rate'),
                'frame': el.findtext('ignition_frame_id'),
                'link': s['link'],
            }
    return None


def cameras(robot):
    """Return the camera-like sensors (camera, depth_camera, rgbd_camera)."""
    out = []
    for s in sensors(robot):
        if s['type'] in ('camera', 'depth_camera', 'rgbd_camera'):
            el = s['el']
            out.append({
                'type': s['type'],
                'hfov_deg': math.degrees(_f(el, 'camera/horizontal_fov')),
                'width': int(_f(el, 'camera/image/width')),
                'height': int(_f(el, 'camera/image/height')),
                'near': _f(el, 'camera/clip/near'),
                'far': _f(el, 'camera/clip/far'),
                'rate_hz': _f(el, 'update_rate'),
                'link': s['link'],
            })
    return out


def has_imu(robot):
    """Return True if an IMU sensor is declared."""
    return any(s['type'] == 'imu' for s in sensors(robot))


def mecanum_plugin(robot):
    """Return the parameters of the MecanumDrive plugin."""
    for p in robot.iter('plugin'):
        if p.get('name', '').endswith('MecanumDrive'):
            return {k: _f(p, k) for k in ('wheel_separation', 'wheelbase', 'wheel_radius')}
    return None


def driven_wheels(robot):
    """Return radius, track and wheelbase of the wheels that the MecanumDrive plugin drives."""
    plugin = next(p for p in robot.iter('plugin') if p.get('name', '').endswith('MecanumDrive'))
    names = [plugin.findtext(k) for k in (
        'front_left_joint', 'front_right_joint', 'back_left_joint', 'back_right_joint')]
    pos, radius = {}, []
    for j in robot.findall('joint'):
        if j.get('name') in names:
            pos[j.get('name')] = _xyz(j.find('origin'))
            link = j.find('child').get('link')
            for ln in robot.findall('link'):
                if ln.get('name') == link:
                    cyl = ln.find('collision/geometry/cylinder')
                    if cyl is not None:
                        radius.append(float(cyl.get('radius')))
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    return {'radius': radius[0] if radius else None,
            'track': max(ys) - min(ys), 'wheelbase': max(xs) - min(xs)}


def total_mass(robot):
    """Return the sum of all link masses in kg."""
    return sum(float(m.get('value')) for m in robot.iter('mass'))


def mounts(robot):
    """Return the x, y, z of the LiDAR and depth-camera joints relative to base_link."""
    out = {}
    for j in robot.findall('joint'):
        if j.get('name') in ('lidar', 'depth_camera', 'imu_joint'):
            out[j.get('name')] = _xyz(j.find('origin'))
    return out
