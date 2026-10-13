#!/bin/bash
set -e

# Needs ROS 2 Humble sourced first (sets ROS_DISTRO) and the system Python, not a conda env.
if [ -z "$ROS_DISTRO" ]; then
        echo "ROS_DISTRO is not set: run 'source /opt/ros/humble/setup.bash' first" >&2
        exit 1
fi
if [ -n "$CONDA_PREFIX" ]; then
        echo "A conda environment is active ($CONDA_PREFIX): run 'conda deactivate' first" >&2
        exit 1
fi

envsubst < src/ros2.repos | vcs import src
sudo apt-get update
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -y --rosdistro=$ROS_DISTRO
