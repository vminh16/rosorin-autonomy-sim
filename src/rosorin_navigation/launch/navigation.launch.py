"""
Nav2 (map_server + AMCL + navigation) for the ROSOrin Pro simulation, with RViz.

Replaces robot_gazebo/launch/include/navigation.launch.py (Hiwonder ROSOrin Pro wiki,
V1.0.0 2025-05-29), which runs the same Nav2 nodes but cannot be used as published: it declares
a controller file config/nav2_controller_teb.yaml that is not in the package, loads the vendor
map map_01 by default, and its params_file default for localization points to a missing params/
directory. This file starts the standard nav2_bringup bringup_launch.py (same nodes, not composed)
with config/nav2_params.yaml (fixed copy of the vendor parameters, see its header) and the map
saved from our SLAM run (maps/house.yaml). Run it after sim.launch.py, without SLAM.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('rosorin_navigation')
    nav2_bringup = get_package_share_directory('nav2_bringup')
    rviz = LaunchConfiguration('rviz')

    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file'),
            'use_sim_time': 'true',
            'autostart': 'true',
            'use_composition': 'False',
            'slam': 'False',
        }.items())

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'nav2_clean.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz))

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=os.path.join(pkg, 'maps', 'house.yaml'),
                              description='map yaml (default: maps/house.yaml of this repo)'),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(pkg, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('rviz', default_value='true'),
        bringup,
        rviz_node,
    ])
