#!/bin/bash
set -e

# Only this project's packages: src/simulations/ is vendored unmodified and fails flake8.
PACKAGES="rosorin_gazebo_plugins rosorin_navigation"
if [ -f install/setup.bash ]; then source install/setup.bash; fi
colcon test --packages-select $PACKAGES
colcon test-result --test-result-base build/rosorin_gazebo_plugins --verbose
colcon test-result --test-result-base build/rosorin_navigation --verbose
