#!/bin/bash
set -e

LINTER="$1"
# Only this project's packages: src/simulations/ is the vendor code, kept unmodified (see README).
PACKAGES="src/rosorin_navigation src/rosorin_gazebo_plugins"

./setup.sh

case "$LINTER" in
  "uncrustify"|"cppcheck"|"cpplint")
    if [ -z "$(find $PACKAGES -name '*.cpp' -o -name '*.hpp' -o -name '*.c' -o -name '*.h')" ]; then
      echo "No C/C++ files found. Skipping $LINTER."
      exit 0
    fi
    ;;
  "flake8"|"pep257")
    if [ -z "$(find $PACKAGES -name '*.py')" ]; then
      echo "No Python files found. Skipping $LINTER."
      exit 0
    fi
    ;;
esac

source "/opt/ros/$ROS_DISTRO/setup.bash"
"ament_${LINTER}" $PACKAGES
