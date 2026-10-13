"""
Launch the ROSOrin Pro simulation in Ignition Gazebo (Fortress).

Fixed copy of robot_gazebo/launch/{worlds,room_worlds,spwan_model,ros_ign_bridge}.launch.py
from the Hiwonder ROSOrin Pro simulation package (wiki 9_Gazebo_Simulation,
.typerc V1.0.0 2025-05-29). Upstream files are left untouched in src/simulations/. Changes:
  - drop get_package_share_directory('holonomic_sim'): not shipped, crashes the launch
  - GUI render engine: ogre2 on a native install (shadows, PBR materials); on WSL2 ogre (v1),
    because ogre2 renders all textured meshes black on D3D12 Mesa (gui_render_engine:=auto)
  - MESA_GL_VERSION_OVERRIDE=4.5 on WSL2 only: Mesa D3D12 reports GL 4.2, ogre2 sensor
    rendering aborts without it
  - no ros2_control_node / joint_state_broadcaster: the URDF has no <ros2_control> tag,
    so both fail; /joint_states already comes from the Ignition JointStatePublisher system
  - no joint_state_publisher: it republished /joint_states onto itself
  - static map->odom TF is opt-in (static_map_tf:=true); it conflicts with slam_toolbox / AMCL
  - /controller/cmd_vel is exposed as /cmd_vel so teleop_twist_keyboard and Nav2 work unchanged
  - DEPTH_CAMERA_TYPE defaults to the .typerc value (aurora), so sourcing .typerc is optional
  - furniture (positions from spawn_objects.launch.py) is spawned as static models: upstream
    spawns 17 dynamic multi-link bodies, which drops the Real Time Factor from 1.0 to ~0.5
  - robocup_home uses worlds/robocup_home.sdf from this package: physics step 0.03 -> 0.01 s
  - realism:=true (default false, the setup of the report): sensor noise as the real sensors and
    odometry that drifts. Gazebo's /odom (true pose) becomes /ground_truth/odom and its TF is not
    used; wheel_odometry publishes /odom_raw from the wheel encoders, robot_localization fuses it
    with the IMU into /odom and the TF odom -> base_footprint, as on the robot (wiki 2.1.4); the
    LiDAR scan comes as /scan_raw and scan_noise publishes /scan with the COIN-D6 noise
  - depth:=true makes the camera an RGB-D camera (/depth_cam/depth/image_raw, /depth_cam/points)
  - robot model is urdf/rosorin_sim.urdf.xacro from this package (wheel kinematics, LiDAR 360 deg,
    camera FOV/rate, IMU, mass) instead of robot_gazebo/urdf/robot.gazebo.xacro; each change is
    explained in the header of that file and checked by test/test_sim_fidelity.py
"""

import os
import re

from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import PackageNotFoundError
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


# (model path under robot_gazebo/models, name, x, y, z, yaw) — copied from spawn_objects.launch.py
FURNITURE = [
    ('bed.model', 'bed', 5.0, -3.9, 0.0, 3.1415926),
    ('sofa.model', 'sofa', -1.0, -3.9, 0.0, 1.57),
    ('tea_table.model', 'tea_table', -2.1, -2.2, 0.0, 1.57),
    ('bookshelft.model', 'bookshelft', 2.0, -0.55, 0.0, -1.57),
    ('table/kitchen_table.model', 'kitchen_table', -3.5, 3.7, 0.0, 1.57),
    ('bottles/red_bottle.model', 'red_bottle', -3.3, 3.55, 0.8, 0.0),
    ('bottles/green_bottle.model', 'green_bottle', -3.6, 3.55, 0.8, 0.0),
    ('cupboard/cupboard_0.model', 'cupboard_0', -2.0, 0.7, 0.0, 1.57),
    ('cupboard/cupboard_1.model', 'cupboard_1', -1.3, 3.7, 0.0, -1.57),
    ('table/dinning_table_0.model', 'dinning_table_0', 1.5, 1.5, 0.0, 1.57),
    ('table/dinning_table_1.model', 'dinning_table_1', 1.5, 2.0, 0.0, 1.57),
    ('table/dinning_table_2.model', 'dinning_table_2', 2.7, 1.5, 0.0, 1.57),
    ('table/dinning_table_3.model', 'dinning_table_3', 2.7, 2.0, 0.0, 1.57),
    ('chair/chair_0.model', 'chair_0', 1.5, 1.2, 0.0, 1.57),
    ('chair/chair_1.model', 'chair_1', 1.5, 2.3, 0.0, -1.57),
    ('chair/chair_2.model', 'chair_2', 2.7, 1.2, 0.0, 1.57),
    ('chair/chair_3.model', 'chair_3', 2.7, 2.3, 0.0, -1.57),
]


def running_on_wsl():
    """Return True inside WSL2, whose D3D12 Mesa driver needs the ogre (v1) GUI."""
    try:
        with open('/proc/sys/kernel/osrelease') as f:
            return 'microsoft' in f.read().lower()
    except OSError:
        return False


def static_model_xml(model_file):
    """Return the URDF model as a static body with absolute mesh paths."""
    model_dir = os.path.dirname(model_file)
    xml = open(model_file).read()
    xml = re.sub(r'filename="(?!/|file:|package:|model:)([^"]+)"',
                 lambda m: 'filename="file://%s"' % os.path.normpath(
                     os.path.join(model_dir, m.group(1))), xml)
    return xml.replace('</robot>', '<gazebo><static>true</static></gazebo>\n</robot>')


def spawn_furniture(robot_gazebo):
    nodes = []
    for rel, name, fx, fy, fz, fyaw in FURNITURE:
        xml = static_model_xml(os.path.join(robot_gazebo, 'models', rel))
        nodes.append(Node(
            package='ros_gz_sim',
            executable='create',
            name='spawn_' + name,
            arguments=['-string', xml, '-name', name, '-x', str(fx), '-y', str(fy),
                       '-z', str(fz), '-Y', str(fyaw)]))
    return nodes


def launch_setup(context):
    world = LaunchConfiguration('world').perform(context)
    gui_engine = LaunchConfiguration('gui_render_engine').perform(context)
    wsl = running_on_wsl()
    if gui_engine == 'auto':
        gui_engine = 'ogre' if wsl else 'ogre2'
    static_map_tf = LaunchConfiguration('static_map_tf').perform(context) == 'true'
    x, y, yaw = (LaunchConfiguration(k).perform(context) for k in ('x', 'y', 'yaw'))
    gui = LaunchConfiguration('gui').perform(context) == 'true'
    furniture = LaunchConfiguration('furniture').perform(context) == 'true'
    camera = LaunchConfiguration('camera').perform(context) == 'true'
    world_override = LaunchConfiguration('world_file').perform(context)
    xacro_override = LaunchConfiguration('robot_xacro').perform(context)
    realism = LaunchConfiguration('realism').perform(context) == 'true'
    depth = LaunchConfiguration('depth').perform(context) == 'true'
    if realism:
        # checked before anything starts: a missing package found later aborts the launch and
        # leaves Gazebo running
        try:
            get_package_share_directory('robot_localization')
        except PackageNotFoundError:
            raise RuntimeError('realism:=true needs robot_localization: '
                               'sudo apt install ros-humble-robot-localization (or ./setup.sh)')

    robot_gazebo = get_package_share_directory('robot_gazebo')
    own_world = os.path.join(get_package_share_directory('rosorin_navigation'), 'worlds',
                             world + '.sdf')
    world_file = world_override or (own_world if os.path.exists(own_world) else
                                    os.path.join(robot_gazebo, 'worlds', world + '.sdf'))
    xacro_file = xacro_override or os.path.join(
        get_package_share_directory('rosorin_navigation'), 'urdf', 'rosorin_sim.urdf.xacro')
    ign_args = f' -r {world_file} --render-engine-gui {gui_engine}' + ('' if gui else ' -s')
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' sim_ign:=true',
                 f' realism:={str(realism).lower()} depth:={str(depth).lower()}']),
        value_type=str)

    ign = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_ign_gazebo'), 'launch', 'ign_gazebo.launch.py')),
        launch_arguments=[('ign_args', ign_args)])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}])

    spawn_robot = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'rosorin', '-allow_renaming', 'true',
                   '-x', x, '-y', y, '-z', '0.0', '-Y', yaw],
        parameters=[{'use_sim_time': True}])

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/controller/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
        ] + ([] if realism else [
            '/odom/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
        ]) + ([
            '/depth_cam/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/depth_cam/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        ] if camera else []) + ([
            '/depth_cam/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/depth_cam/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
        ] if camera and depth else []),
        remappings=[
            ('/controller/cmd_vel', '/cmd_vel'),
            ('/depth_cam/image', '/depth_cam/rgb/image_raw'),
            ('/depth_cam/camera_info', '/depth_cam/rgb/camera_info'),
            ('/depth_cam/depth_image', '/depth_cam/depth/image_raw'),
        ] + ([
            ('/odom', '/ground_truth/odom'),
            ('/scan', '/scan_raw'),
        ] if realism else [
            ('/odom/tf', '/tf'),
        ]),
        parameters=[{'use_sim_time': True}])

    realism_nodes = [
        Node(package='rosorin_navigation', executable='scan_noise', output='screen',
             parameters=[{'use_sim_time': True}]),
        Node(package='rosorin_navigation', executable='wheel_odometry', output='screen',
             parameters=[{'use_sim_time': True}]),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             output='screen',
             parameters=[os.path.join(get_package_share_directory('rosorin_navigation'),
                                      'config', 'ekf.yaml'), {'use_sim_time': True}],
             remappings=[('odometry/filtered', 'odom')]),
    ] if realism else []

    actions = [SetEnvironmentVariable('MESA_GL_VERSION_OVERRIDE', '4.5')] if wsl else []
    actions += [
        SetEnvironmentVariable('DEPTH_CAMERA_TYPE', os.environ.get('DEPTH_CAMERA_TYPE', 'aurora')),
        ign, robot_state_publisher, spawn_robot, bridge,
    ] + realism_nodes
    if world == 'robocup_home' and furniture:
        actions += spawn_furniture(robot_gazebo)
    if static_map_tf:
        actions.append(Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['--frame-id', 'map', '--child-frame-id', 'odom'],
            parameters=[{'use_sim_time': True}]))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='robocup_home',
                              description='robocup_home (furnished house) or empty'),
        DeclareLaunchArgument('gui_render_engine', default_value='auto',
                              description='auto (ogre2, or ogre on WSL2), ogre or ogre2'),
        DeclareLaunchArgument('static_map_tf', default_value='false',
                              description='publish map->odom identity; only without SLAM/AMCL'),
        DeclareLaunchArgument('gui', default_value='true', description='false = server only'),
        DeclareLaunchArgument('furniture', default_value='true',
                              description='spawn the furniture into robocup_home'),
        DeclareLaunchArgument('camera', default_value='true',
                              description='bridge the RGB camera to ROS'),
        DeclareLaunchArgument('world_file', default_value='',
                              description='absolute .sdf path, overrides world'),
        DeclareLaunchArgument('realism', default_value='false',
                              description='true: sensor noise, drifting odometry fused by an EKF'),
        DeclareLaunchArgument('depth', default_value='false',
                              description='true: RGB-D camera (depth image and point cloud)'),
        DeclareLaunchArgument('robot_xacro', default_value='',
                              description='absolute .xacro path, overrides the Hiwonder URDF'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=launch_setup),
    ])
