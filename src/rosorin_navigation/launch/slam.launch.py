"""
SLAM (slam_toolbox, sync mode) for the ROSOrin Pro simulation, with RViz.

Fixed copy of robot_gazebo/launch/include/slam.launch.py (Hiwonder ROSOrin Pro wiki,
V1.0.0 2025-05-29). Changes: no dependency on the `need_compile` variable from .typerc,
and RViz runs with use_sim_time:=true (upstream starts it on wall-clock time).
Parameters are the upstream config/slam.yaml.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_gazebo = get_package_share_directory('robot_gazebo')
    rviz = LaunchConfiguration('rviz')

    slam = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[os.path.join(robot_gazebo, 'config', 'slam.yaml'), {
            'use_sim_time': True,
            'map_frame': 'map',
            'odom_frame': 'odom',
            'base_frame': 'base_footprint',
        }])

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(robot_gazebo, 'rviz', 'slam.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz))

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        slam,
        rviz_node,
    ])
