#!/bin/bash
# Install everything the workspace needs on Ubuntu 22.04 with ROS 2 Humble already installed.
# Usage (from the repository root):  source /opt/ros/humble/setup.bash && ./setup.sh
set -e

step() { printf '\n\033[1;34m[%s] %s\033[0m\n' "$1" "$2"; }

step 1/4 "Checking the environment"
if [ -z "$ROS_DISTRO" ]; then
        echo "ROS_DISTRO is not set: run 'source /opt/ros/humble/setup.bash' first" >&2
        exit 1
fi
if [ -n "$CONDA_PREFIX" ]; then
        echo "A conda environment is active ($CONDA_PREFIX): run 'conda deactivate' first" >&2
        exit 1
fi
echo "ROS 2 $ROS_DISTRO, $(. /etc/os-release && echo "$PRETTY_NAME"), python3 = $(command -v python3)"

step 2/4 "Installing the simulation, SLAM and navigation packages"
sudo apt-get update
sudo apt-get install -y \
        ros-$ROS_DISTRO-ros-gz-sim ros-$ROS_DISTRO-ros-gz-bridge ros-$ROS_DISTRO-ros-ign-gazebo ros-$ROS_DISTRO-ros-ign-bridge \
        ros-$ROS_DISTRO-navigation2 ros-$ROS_DISTRO-nav2-bringup ros-$ROS_DISTRO-nav2-simple-commander \
        ros-$ROS_DISTRO-slam-toolbox \
        ros-$ROS_DISTRO-robot-localization \
        ros-$ROS_DISTRO-teleop-twist-keyboard \
        ros-$ROS_DISTRO-xacro ros-$ROS_DISTRO-robot-state-publisher \
        python3-numpy python3-yaml python3-pytest

step 3/4 "Installing the remaining dependencies declared in the package.xml files (rosdep)"
vcs import src < src/ros2.repos                 # empty: the vendor simulation is already in src/
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -y --rosdistro=$ROS_DISTRO

step 4/4 "Done"
echo "Next: ./build.sh && source install/setup.bash"
