cmake_minimum_required(VERSION 3.8)
project(rosorin_gazebo_plugins)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(ignition-gazebo6 REQUIRED)
find_package(ignition-plugin1 REQUIRED COMPONENTS register)
find_package(ignition-transport11 REQUIRED)
find_package(ignition-msgs8 REQUIRED)

# Gazebo system plugin, loaded from the URDF as filename="rosorin_planar_drive"
add_library(rosorin_planar_drive SHARED src/planar_drive.cpp)
target_link_libraries(rosorin_planar_drive
  ignition-gazebo6::ignition-gazebo6
  ignition-plugin1::register
  ignition-transport11::ignition-transport11
  ignition-msgs8::ignition-msgs8)
install(TARGETS rosorin_planar_drive LIBRARY DESTINATION lib)

# sourcing install/setup.bash adds <prefix>/lib to IGN_GAZEBO_SYSTEM_PLUGIN_PATH
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/${PROJECT_NAME}.dsv.in")

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
