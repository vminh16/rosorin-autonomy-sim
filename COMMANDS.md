# Verified commands

Commands that ran successfully, copied verbatim. In every terminal first run
`source /opt/ros/humble/setup.bash && source install/setup.bash` from the repository root.
Test machines: Ubuntu 22.04.5 native (from 2026-10-13) and in WSL2 (until 2026-10-12), ROS 2 Humble, Ignition Gazebo 6.18
(Fortress), RTX 2050. Rows are newest first; a later row supersedes an earlier one for the same step.

| Date | Step | Command | Result |
|---|---|---|---|
| 2026-10-14 | Single goals, true pose | `ros2 run rosorin_navigation waypoint_follower --ros-args -p single_goals:=true -p waypoints_file:=src/rosorin_navigation/config/single_goals.yaml -p true_pose_topic:=odom` | After `sim.launch.py gui:=false` and `navigation.launch.py rviz:=false`. 6/6, 15.9 s per goal (bedroom U-turn 28.9 s), final error against the true pose 0.109 m mean, 0.165 m max; `results/nav_runs/20261014-120611.csv` |
| 2026-10-14 | Short route, true pose | `ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml -p true_pose_topic:=odom` | 7/7, 34.2 m in 119 s, true error 0.123 m mean, 0.271 m max (AMCL 0.132 / 0.237); `results/nav_runs/20261014-120750.csv` |
| 2026-10-14 | Long route, true pose | `ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints_extended.yaml -p true_pose_topic:=odom` | 14/14, 58.5 m in 215 s, true error 0.118 m mean, 0.225 m max; `results/nav_runs/20261014-120952.csv` |
| 2026-10-14 | RViz "2D Goal Pose" | `ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped "{header: {frame_id: map}, pose: {position: {x: 0.5, y: 3.0}, orientation: {w: 1.0}}}"` | bt_navigator: "Goal succeeded" after 24 s. `/goal_pose` is the topic of the RViz "2D Goal Pose" tool (in `nav2_clean.rviz`); the mouse click itself was not scripted |
| 2026-10-14 | Package tests | `./test.sh` | 27 tests (8 + 19), 0 failures |
| 2026-10-14 | Autonomous mapping | `slam.launch.py rviz:=false`, `navigation.launch.py slam:=true rviz:=false`, `ros2 run rosorin_navigation waypoint_follower --ros-args -p localizer:=slam` | 7/7 waypoints in 112 s (twice); saved map 203 x 162 cells |
| 2026-10-14 | Realism mode | `ros2 launch rosorin_navigation sim.launch.py realism:=true depth:=true` | RTF 1.00; `/scan` 10 Hz, `/odom_raw` 47 Hz, `/odom` (EKF) 50 Hz, depth 12 Hz (0.65-3.0 m in the empty world), points 11 Hz; 1 m square: wheel odometry 1.8 cm / 3.0 deg off, EKF 0.8 cm / 1.3 deg |
| 2026-10-14 | Navigation, realism mode | `sim.launch.py realism:=true`, `navigation.launch.py rviz:=false`, `waypoint_follower` with `waypoints.yaml` | 7/7, 16.1 s per waypoint, final error (AMCL) 0.166 m mean, 0.254 m max |
| 2026-10-14 | SLAM, realism mode | `sim.launch.py realism:=true`, `slam.launch.py rviz:=false`, 1 m square | map 204 x 162 cells, map->odom correction 1.5 cm |
| 2026-10-14 | Clean rebuild, native Ubuntu 22.04 | `rm -rf build install log && ./build.sh && source install/setup.bash && ./test.sh` | 4 packages build; 24 tests, 0 failures; 13 fidelity tests pass; `sim.launch.py` with GUI and headless, `probe_motion.py` ratios 1.00 / 1.00 / 1.00 |
| 2026-10-12 | Build | `colcon build --symlink-install` | 4 packages (`robot_gazebo`, `rosorin_description`, `rosorin_gazebo_plugins`, `rosorin_navigation`) build; source `install/setup.bash` again afterwards so Gazebo finds the drive plugin |
| 2026-10-12 | Package tests | `colcon test --packages-select rosorin_gazebo_plugins rosorin_navigation && colcon test-result` | 24 tests, 0 failures (fidelity, flake8, pep257, uncrustify, lint_cmake, xmllint) |
| 2026-10-12 | Simulation | `ros2 launch rosorin_navigation sim.launch.py` | Robot and 17 static furniture models in `robocup_home`, RTF 1.000 |
| 2026-10-12 | Simulation | `ros2 launch rosorin_navigation sim.launch.py world:=empty` | RTF 1.000 |
| 2026-10-12 | Headless simulation | `ros2 launch rosorin_navigation sim.launch.py gui:=false world:=empty` | Server without GUI, RTF 1.000, used for automated checks |
| 2026-10-12 | Spec check | `python3 -m pytest src/rosorin_navigation/test/test_sim_fidelity.py -q` | 13 passed (URDF against the wiki, drive and `/odom` checks), no simulator needed |
| 2026-10-12 | Motion check | `python3 tools/probe_motion.py --speed 0.2 --turn 0.5 --seconds 4` | forward / sideways / turn = 1.00 / 1.00 / 1.00 (needs a running simulation) |
| 2026-10-12 | Collision check | `python3 tools/probe_collision.py` | 9/9 PASS: max tilt 0.6 deg, max z 0.003 m with a 1 m/s command into walls and furniture (measured at `79aeecc`; since `6916228` the drive limits the robot to 0.461 m/s, still 9/9) (needs the furnished house running; exit code 1 on FAIL) |
| 2026-10-12 | Physics check | `python3 tools/probe_physics.py` | 7/7 PASS (empty world): no creep at rest, IMU 9.800 m/s2, step 63% in 0.108 s, stop in 0.34 s, top speed 0.461 m/s and 2.643 rad/s (motor limit) |
| 2026-10-12 | Odometry source | `ign topic -i -t /odom` | 1 publisher (`OdometryPublisher`) |
| 2026-10-12 | RTF | `ign topic -e -t /stats -n 60 \| grep real_time_factor` | 1.000 with SLAM and RViz running |
| 2026-10-12 | Drive | `ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"` | `/odom` x grows 0 -> 0.76 m |
| 2026-10-12 | LiDAR | `ros2 topic hz /scan` | 9.95 Hz, 400 beams, frame `lidar_frame` |
| 2026-10-12 | SLAM | `ros2 launch rosorin_navigation slam.launch.py` | RViz opens (~57 fps), `/map` published, `map->odom` comes from slam_toolbox |
| 2026-10-12 | Teleop | `ros2 run teleop_twist_keyboard teleop_twist_keyboard` | Robot follows the keys. Teleop 2.4.1 accepts `-p speed:=0.25 -p turn:=0.5` (defaults 0.5 / 1.0); `z` lowers both by 10% |
| 2026-10-12 | Save map | `ros2 run nav2_map_server map_saver_cli -f <path>/<name> --ros-args -p use_sim_time:=true -p map_subscribe_transient_local:=true` | Writes `.pgm` + `.yaml` from the slam_toolbox `/map` (tested into a temporary directory). `map_subscribe_transient_local` comes from wiki 5.1 |
| 2026-10-12 | Save map | `ros2 run nav2_map_server map_saver_cli -f maps/house --ros-args -p use_sim_time:=true -p map_subscribe_transient_local:=true` | `maps/house.{pgm,yaml}`, 205x169 cells at 0.05 m; 99.7% of the world's walls detected, 80% of occupied cells within 0.1 m of a wall (the rest is furniture), no global offset. The RViz screenshot tool gives a black image on this setup, use an OS screenshot |
| 2026-10-12 | Map info | `ros2 topic echo --once /map --field info` | `resolution`, `width`, `height`, `origin` of the map being built |
| 2026-10-12 | TF | `ros2 run tf2_ros tf2_echo map odom` | `map->odom` published by slam_toolbox |
| 2026-10-12 | True pose | `ign topic -e -t /world/robot_world/pose/info -n 1` | True pose of `rosorin` (the world is named `robot_world`). Used to check whether the robot left the house (x in [-5, 5], y in [-4, 4]) |
| 2026-10-12 | Expand URDF | `DEPTH_CAMERA_TYPE=aurora xacro src/rosorin_navigation/urdf/rosorin_sim.urdf.xacro` | Full URDF of the simulated robot |
| 2026-10-12 | Clean up | `pkill -f "ign gazebo"; pkill -x rviz2; pkill -f slam_toolbox` | No simulation process left |
| 2026-10-12 | Navigation | `ros2 launch rosorin_navigation navigation.launch.py rviz:=false` | After `sim.launch.py`, without SLAM. map_server (`maps/house.yaml`), AMCL (starts at the spawn pose), MPPI controller; both lifecycle managers report "Managed nodes are active". Tested headless (`sim.launch.py gui:=false`) |
| 2026-10-12 | Multi-waypoint | `ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml` | 7/7 waypoints in 112 s, run twice (14/14); writes `results/nav_runs/<timestamp>.csv`, exit code 1 if a waypoint fails |
| 2026-10-12 | Multi-waypoint, long route | `ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints_extended.yaml` | 14/14 waypoints, 56.6 m in 216 s, on the GUI simulation with RViz (the robot started at (2.18, 0.90), where the route was generated from) |

## TurtleBot3 baseline (Gazebo Classic)

| Date | Step | Command | Result |
|---|---|---|---|
| 2026-10-12 | Gazebo | `ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py` | burger spawns, 62 FPS, RTF 1.00 |
| 2026-10-12 | Nav2 | `ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True map:=/opt/ros/humble/share/nav2_bringup/maps/turtlebot3_world.yaml` | Navigation and localization active |
| 2026-10-12 | RViz | `rviz2 -d src/rosorin_navigation/rviz/nav2_clean.rviz --ros-args -p use_sim_time:=true` | Robot model visible, no particle cloud |
