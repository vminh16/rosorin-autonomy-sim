#!/bin/bash
set -e

# Same layout as the README (`colcon build --symlink-install`, isolated install/<pkg>/).
# Do not add --merge-install: colcon refuses to mix layouts in one install/ directory
# ("The install directory 'install' was created with the layout 'merged'").
BUILD_TYPE=RelWithDebInfo
colcon build \
        --symlink-install \
        --cmake-args "-DCMAKE_BUILD_TYPE=$BUILD_TYPE" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On" \
        -Wall -Wextra -Wpedantic
