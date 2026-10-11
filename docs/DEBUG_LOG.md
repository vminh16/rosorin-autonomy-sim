# Debug Log

Nguồn trực tiếp cho mục "Problems Encountered & Solutions" của báo cáo. Ghi NGAY khi gặp lỗi, không đợi sửa xong.
Thêm mục mới lên trên cùng. Dùng skill `/log-issue` để tạo mục theo đúng mẫu.

<!--
Mẫu một mục:

## ISSUE-NNN — <tiêu đề ngắn>
- Ngày: YYYY-MM-DD
- Thành phần: Env/WSL | Gazebo | SLAM | Nav2 | rosorin_navigation | Build/CI
- Trạng thái: OPEN | FIXED | WORKAROUND | WONTFIX
- Lệnh gây lỗi:
  ```bash
  <lệnh chính xác>
  ```
- Lỗi (trích dòng quan trọng nhất, không dán cả log):
  ```
  <message>
  ```
- Nguyên nhân: <đã xác minh hay chỉ là giả thuyết — ghi rõ>
- Cách sửa: <thay đổi cụ thể: file, dòng, version, lệnh>
- Thời gian mất: <giờ>
- Đưa vào báo cáo: yes | no
-->

## ISSUE-012 — Real Time Factor của ROSOrin chỉ 0.7–0.95
- Ngày: 2026-10-12
- Thành phần: Gazebo
- Trạng thái: OPEN
- Lệnh gây lỗi: `ros2 launch rosorin_navigation sim.launch.py`
- Lỗi: `ign topic -e -t /stats` → `real_time_factor: 0.67–0.93`; `/scan` cấu hình 10 Hz nhưng đo được ~5.5 Hz.
- Nguyên nhân: giả thuyết: server render bằng ogre2 cho `gpu_lidar` + depth camera (`aurora`) mỗi bước; TurtleBot3 (Gazebo Classic, không camera) đạt RTF 1.00 trên cùng máy.
- Cách sửa: chưa. Hướng thử: tắt depth camera trong bản copy URDF, hoặc giảm `update_rate` camera.
- Thời gian mất: —
- Đưa vào báo cáo: yes

## ISSUE-011 — IMU của ROSOrin không phát dữ liệu
- Ngày: 2026-10-12
- Thành phần: Gazebo
- Trạng thái: OPEN
- Lệnh gây lỗi: `ros2 topic hz /imu`
- Lỗi: topic `/imu` tồn tại (do bridge tạo) nhưng không có message; `ign topic -l` không có topic IMU.
- Nguyên nhân (đã xác minh): `robot.gazebo.xacro` của Hiwonder load system `Imu` nhưng không include `imu.gazebo.xacro`, nên không có sensor IMU nào.
- Cách sửa: chưa cần (slam_toolbox và Nav2 không dùng IMU). Nếu cần: include `imu.gazebo.xacro` trong bản copy URDF.
- Thời gian mất: —
- Đưa vào báo cáo: no

## ISSUE-010 — Bridge của Hiwonder luôn phát TF tĩnh `map→odom`
- Ngày: 2026-10-12
- Thành phần: Gazebo, SLAM
- Trạng thái: FIXED
- Lệnh gây lỗi: `ros2 launch robot_gazebo room_worlds.launch.py` rồi `ros2 launch robot_gazebo slam.launch.py` (theo wiki)
- Lỗi: hai nguồn cùng phát `map→odom` (static TF trong `ros_ign_bridge.launch.py` và `spwan_model.launch.py`, cộng slam_toolbox/AMCL).
- Nguyên nhân (đã xác minh, đọc code): `map_static_tf` được trả về vô điều kiện, không phụ thuộc tham số `nav`.
- Cách sửa: `rosorin_navigation/launch/sim.launch.py` tự dựng bridge, TF tĩnh chỉ bật khi `static_map_tf:=true`.
  Kiểm tra: với SLAM chạy, `tf2_echo map odom` chỉ ra giá trị từ slam_toolbox.
- Thời gian mất: 0.2h
- Đưa vào báo cáo: yes

## ISSUE-009 — `ros2_control_node` crash: URDF không có thẻ `<ros2_control>`
- Ngày: 2026-10-12
- Thành phần: Gazebo
- Trạng thái: WORKAROUND
- Lệnh gây lỗi: `room_worlds.launch.py` (gọi `spwan_model.launch.py`)
- Lỗi:
  ```
  [gz_ros2_control]: Error parsing URDF in gz_ros2_control plugin, plugin not active : no ros2_control tag
  [ERROR] [ros2_control_node-2]: process has died [... exit code -6 ...]
  [spawner_joint_state_broadcaster]: Could not contact service /controller_manager/list_controllers
  ```
- Nguyên nhân (đã xác minh): URDF dùng plugin `MecanumDrive` của Ignition để lái và `JointStatePublisher` để phát `/joint_states`; cấu hình ros2_control (`robot_config.yaml`, diff_drive) là phần thừa không khớp robot.
- Cách sửa: `sim.launch.py` bỏ `ros2_control_node`, spawner và `joint_state_publisher` (node này còn phát lại `/joint_states` lên chính nó). Lỗi `gz_ros2_control` vẫn in ra một dòng nhưng vô hại.
- Thời gian mất: 0.2h
- Đưa vào báo cáo: yes

## ISSUE-008 — Nội thất trong Gazebo bị đen toàn bộ (ogre2 trên WSL2)
- Ngày: 2026-10-12
- Thành phần: Env/WSL, Gazebo
- Trạng thái: FIXED
- Lệnh gây lỗi: `room_worlds.launch.py` (GUI dùng `<engine>ogre2</engine>` trong world SDF)
- Lỗi: mọi mesh có texture (sofa, giường, bàn) hiện màu đen đặc. Ảnh: `docs/images/gazebo_ogre2_black.png`.
- Nguyên nhân (đã xác minh bằng so sánh): mesh và texture đã cài đủ; mở GUI thứ hai với `ign gazebo -g --render-engine-gui ogre` trên cùng server thì texture hiện đúng. Lỗi nằm ở ogre2 trên Mesa D3D12 của WSL.
- Cách sửa: `sim.launch.py` thêm `--render-engine-gui ogre` (tham số `gui_render_engine`, mặc định `ogre`). Server vẫn dùng ogre2 cho cảm biến.
- Thời gian mất: 0.3h
- Đưa vào báo cáo: yes

## ISSUE-007 — Ignition crash `OGRE EXCEPTION ... GL3PlusTextureGpu::copyTo`
- Ngày: 2026-10-12
- Thành phần: Env/WSL, Gazebo
- Trạng thái: FIXED
- Lệnh gây lỗi: `room_worlds.launch.py`
- Lỗi:
  ```
  [ign gazebo-1] terminate called after throwing an instance of 'Ogre::UnimplementedException'
  [ign gazebo-1]   what():  OGRE EXCEPTION(9:UnimplementedException):  in GL3PlusTextureGpu::copyTo
  ... in ignition::gazebo::v6::systems::SensorsPrivate::RenderThread()
  ```
- Nguyên nhân (đã xác minh): `glxinfo` báo `Max core profile version: 4.2` với Mesa D3D12; render thread của Sensors system (ogre2, cho gpu_lidar + depth camera) cần tính năng GL cao hơn.
- Cách sửa: `MESA_GL_VERSION_OVERRIDE=4.5` (đặt sẵn trong `sim.launch.py`). Sau khi sửa: không crash, `/scan` có dữ liệu.
- Thời gian mất: 0.2h
- Đưa vào báo cáo: yes

## ISSUE-006 — `package 'holonomic_sim' not found` khi chạy launch theo wiki
- Ngày: 2026-10-12
- Thành phần: Gazebo
- Trạng thái: FIXED
- Lệnh gây lỗi:
  ```bash
  ros2 launch robot_gazebo worlds.launch.py
  ```
- Lỗi:
  ```
  [ERROR] [launch]: Caught exception in launch (see debug for traceback): "package 'holonomic_sim' not found, ...
  ```
- Nguyên nhân (đã xác minh): `worlds.launch.py` và `room_worlds.launch.py` gọi `get_package_share_directory('holonomic_sim')` nhưng gói này không có trong `simulations.zip`; biến kết quả không được dùng. Thêm nữa, xacro cần biến `DEPTH_CAMERA_TYPE` từ `.typerc` (`environment variable 'DEPTH_CAMERA_TYPE' is not set`).
- Cách sửa: launch mới `ros2 launch rosorin_navigation sim.launch.py` (bỏ dòng `holonomic_sim`, mặc định `DEPTH_CAMERA_TYPE=aurora`). Bản gốc giữ nguyên.
- Thời gian mất: 0.2h
- Đưa vào báo cáo: yes

## ISSUE-005 — RViz mờ nhòe khi robot di chuyển (config Nav2 mặc định)
- Ngày: 2026-10-12
- Thành phần: Nav2 (TurtleBot3 burger)
- Trạng thái: FIXED
- Lệnh gây lỗi:
  ```bash
  ros2 launch nav2_bringup rviz_launch.py
  ```
- Lỗi: khi robot chạy, quanh robot là một đám mũi tên xanh nhấp nháy, không thấy hình robot.
- Nguyên nhân (đã xác minh bằng ảnh chụp cửa sổ RViz): `nav2_default_view.rviz` bật "Amcl Particle Swarm" (hàng trăm mũi tên, vẽ lại mỗi khung hình) và tắt "RobotModel". `rviz_launch.py` của Humble cũng không truyền `use_sim_time`. Khung hình RViz tự nó vẫn sắc nét.
- Cách sửa: dùng `src/rosorin_navigation/rviz/nav2_clean.rviz` (RobotModel bật, particle tắt):
  ```bash
  rviz2 -d src/rosorin_navigation/rviz/nav2_clean.rviz --ros-args -p use_sim_time:=true
  ```
  Phần nhòe còn lại khi chuyển động (nếu có) là giả thuyết do WSLg nén hình qua RDP, chưa xác minh.
- Thời gian mất: 0.3h
- Đưa vào báo cáo: yes

## ISSUE-004 — Costmap có vật cản "ma", goal bị aborted
- Ngày: 2026-10-12
- Thành phần: Nav2 (TurtleBot3 burger, kiểm thử pipeline)
- Trạng thái: FIXED
- Lệnh gây lỗi: đặt "2D Pose Estimate" bằng tay trong RViz, sau đó gửi "2D Goal Pose".
- Lỗi: costmap hiện vật cản ở chỗ không có tường; Nav2 báo goal `ABORTED`.
- Nguyên nhân (đã xác minh): 2D Pose Estimate đặt sai hướng → AMCL khởi tạo lệch so với pose thật,
  scan LiDAR bị chiếu sai lên map và đánh dấu thành vật cản trên costmap.
- Cách sửa:
  1. Lấy pose thật của robot trong Gazebo:
     ```bash
     gz model -m burger -p
     ```
  2. Publish `/initialpose` từ tọa độ đó (thay `<x> <y>` và quaternion `<qz> <qw>` của yaw):
     ```bash
     ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
       "{header: {frame_id: map}, pose: {pose: {position: {x: <x>, y: <y>}, orientation: {z: <qz>, w: <qw>}}}}"
     ```
  3. Xóa costmap cũ:
     ```bash
     ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap
     ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap
     ```
- Thời gian mất: — (chưa ghi)
- Đưa vào báo cáo: yes

## ISSUE-003 — Gazebo FPS 5.8, mô phỏng rất chậm trên WSL2
- Ngày: 2026-10-12
- Thành phần: Env/WSL, Gazebo
- Trạng thái: FIXED
- Lệnh gây lỗi: mở Gazebo với TurtleBot3 `waffle`.
- Lỗi: Gazebo hiển thị FPS ≈ 5.8, Real Time Factor thấp, Nav2 phản hồi trễ.
- Nguyên nhân (đã xác minh): WSLg render qua D3D12 bằng iGPU Intel thay vì GPU NVIDIA RTX;
  model `waffle` (có camera) nặng hơn `burger`; WSL thiếu RAM.
- Cách sửa:
  1. Ép Mesa dùng GPU NVIDIA (thêm vào `~/.bashrc`):
     ```bash
     export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
     ```
     Kiểm tra: `glxinfo -B | grep -i renderer` phải ra NVIDIA.
  2. Đổi model: `export TURTLEBOT3_MODEL=burger` (thay cho `waffle`).
  3. Tăng RAM cho WSL trong `%UserProfile%\.wslconfig` (Windows), rồi `wsl --shutdown`:
     ```ini
     [wsl2]
     memory=8GB
     ```
- Kết quả sau khi sửa: FPS 61, Real Time Factor 0.99.
- Thời gian mất: — (chưa ghi)
- Đưa vào báo cáo: yes

## ISSUE-002 — Nav2 báo `Invalid frame ID "odom"`: robot không spawn trong Gazebo
- Ngày: 2026-10-12
- Thành phần: Gazebo, Nav2
- Trạng thái: FIXED
- Lệnh gây lỗi: một launch gộp chạy cùng lúc Gazebo + Nav2 bringup + RViz.
- Lỗi:
  ```
  Invalid frame ID "odom" ...
  ```
- Nguyên nhân (đã xác minh): launch gộp bị timeout khi spawn robot (Gazebo khởi động chậm trên WSL),
  robot không xuất hiện → không có `/odom` và TF `odom→base_footprint`. Tiến trình `gzserver` cũ còn sót
  từ lần chạy trước làm tình trạng tệ hơn.
- Cách sửa: dọn tiến trình cũ rồi tách thành 3 terminal, chỉ mở terminal sau khi terminal trước đã sẵn sàng:
  ```bash
  pkill -f gzserver; pkill -f gzclient; pkill -f rviz2
  # T1: Gazebo — đợi robot hiện trong cửa sổ Gazebo
  # T2: Nav2 bringup (use_sim_time:=True, map:=...)
  # T3: RViz
  ```
  Lệnh nguyên văn của từng terminal: chép vào `COMMANDS.md` khi chạy lại.
- Thời gian mất: — (chưa ghi)
- Đưa vào báo cáo: yes

## ISSUE-001 — WSL mặc định cài Ubuntu 24.04, ROS 2 Humble cần 22.04
- Ngày: 2026-10-12
- Thành phần: Env/WSL
- Trạng thái: FIXED
- Lệnh gây lỗi: `wsl --install` (distro mặc định là Ubuntu 24.04).
- Lỗi: không có gói `ros-humble-*` cho Ubuntu 24.04 (Noble); Humble chỉ phát hành binary cho 22.04 (Jammy).
- Nguyên nhân (đã xác minh): ROS 2 Humble target Ubuntu 22.04.
- Cách sửa: cài distro riêng trong PowerShell rồi làm việc trong distro đó:
  ```powershell
  wsl --install -d Ubuntu-22.04
  ```
- Thời gian mất: — (chưa ghi)
- Đưa vào báo cáo: yes
