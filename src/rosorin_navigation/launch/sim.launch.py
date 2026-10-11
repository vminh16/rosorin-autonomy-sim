"""
Launch the ROSOrin Pro simulation in Ignition Gazebo (Fortress).

Fixed copy of robot_gazebo/launch/{worlds,room_worlds,spwan_model,ros_ign_bridge}.launch.py
from the Hiwonder ROSOrin Pro simulation package (wiki 9_Gazebo_Simulation,
.typerc V1.0.0 2025-05-29). Upstream files are left untouched in src/simulations/. Changes:
  - drop get_package_share_directory('holonomic_sim'): not shipped, crashes the launch
  - GUI uses ogre (v1): ogre2 renders all textured meshes black on WSL2 D3D12 Mesa
  - MESA_GL_VERSION_OVERRIDE=4.5: Mesa D3D12 reports GL 4.2, ogre2 sensor rendering
    aborts without it
  - no ros2_control_node / joint_state_broadcaster: the URDF has no <ros2_control> tag,
    so both fail; /joint_states already comes from the Ignition JointStatePublisher system
  - no joint_state_publisher: it republished /joint_states onto itself
  - static map->odom TF is opt-in (static_map_tf:=true); it conflicts with slam_toolbox / AMCL
  - /controller/cmd_vel is exposed as /cmd_vel so teleop_twist_keyboard and Nav2 work unchanged
  - DEPTH_CAMERA_TYPE defaults to the .typerc value (aurora), so sourcing .typerc is optional
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def launch_setup(context):
    world = LaunchConfiguration('world').perform(context)
    gui_engine = LaunchConfiguration('gui_render_engine').perform(context)
    static_map_tf = LaunchConfiguration('static_map_tf').perform(context) == 'true'
    x, y, yaw = (LaunchConfiguration(k).perform(context) for k in ('x', 'y', 'yaw'))

    robot_gazebo = get_package_share_directory('robot_gazebo')
    world_file = os.path.join(robot_gazebo, 'worlds', world + '.sdf')
    xacro_file = os.path.join(robot_gazebo, 'urdf', 'robot.gazebo.xacro')
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' sim_ign:=true']), value_type=str)

    ign = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_ign_gazebo'), 'launch', 'ign_gazebo.launch.py')),
        launch_arguments=[('ign_args', f' -r {world_file} --render-engine-gui {gui_engine}')])

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
            '/odom/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
            '/depth_cam/depth_cam@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/depth_cam/rgb/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        ],
        remappings=[('/odom/tf', '/tf'), ('/controller/cmd_vel', '/cmd_vel')],
        parameters=[{'use_sim_time': True}])

    actions = [
        SetEnvironmentVariable('MESA_GL_VERSION_OVERRIDE', '4.5'),
        SetEnvironmentVariable('DEPTH_CAMERA_TYPE', os.environ.get('DEPTH_CAMERA_TYPE', 'aurora')),
        ign, robot_state_publisher, spawn_robot, bridge,
    ]
    if world == 'robocup_home':
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(robot_gazebo, 'launch', 'spawn_objects.launch.py'))))
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
        DeclareLaunchArgument('gui_render_engine', default_value='ogre',
                              description='ogre (works on WSL2) or ogre2'),
        DeclareLaunchArgument('static_map_tf', default_value='false',
                              description='publish map->odom identity; only without SLAM/AMCL'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=launch_setup),
    ])
