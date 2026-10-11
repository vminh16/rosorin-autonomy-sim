# Verified Commands

Lệnh đã chạy thành công, chép nguyên văn. Mỗi terminal: `source /opt/ros/humble/setup.bash && source install/setup.bash` tại gốc repo.
Môi trường kiểm thử: WSL2 Ubuntu 22.04.5, ROS 2 Humble, Ignition Gazebo 6.18 (Fortress), RTX 2050.

| Ngày | Bước | Lệnh | Kết quả |
|---|---|---|---|
| 2026-10-12 | Build | `colcon build --symlink-install` | 3 package (`robot_gazebo`, `rosorin_description`, `rosorin_navigation`) build OK |
| 2026-10-12 | Mô phỏng | `ros2 launch rosorin_navigation sim.launch.py` | Robot spawn trong `robocup_home`, RTF 0.7–0.95 |
| 2026-10-12 | Di chuyển | `ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}"` | `/odom` x tăng 0 → 0.76 m |
| 2026-10-12 | LiDAR | `ros2 topic hz /scan` | ~5.5 Hz (wall clock), frame `lidar_frame` |
| 2026-10-12 | SLAM | `ros2 launch rosorin_navigation slam.launch.py` | RViz mở, `/map` 202×162 @ 0.05 m, `map→odom` do slam_toolbox phát |
| 2026-10-12 | Dọn tiến trình | `pkill -f "ign gazebo"; pkill -x rviz2; pkill -f slam_toolbox` | Không còn tiến trình mô phỏng |

## TurtleBot3 baseline (Gazebo Classic)

| Ngày | Bước | Lệnh | Kết quả |
|---|---|---|---|
| 2026-10-12 | Gazebo | `ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py` | burger spawn, FPS 62, RTF 1.00 |
| 2026-10-12 | Nav2 | `ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True map:=/opt/ros/humble/share/nav2_bringup/maps/turtlebot3_world.yaml` | Navigation + Localization active |
| 2026-10-12 | RViz | `rviz2 -d src/rosorin_navigation/rviz/nav2_clean.rviz --ros-args -p use_sim_time:=true` | Robot model hiện, không còn particle cloud |

## Chưa xác minh (đã ghi trong README nhưng chưa chạy thử)
- `ros2 run teleop_twist_keyboard teleop_twist_keyboard` với ROSOrin (cần terminal tương tác)
- `ros2 run nav2_map_server map_saver_cli -f maps/house --ros-args -p use_sim_time:=true`
- Navigation trên map đã lưu
