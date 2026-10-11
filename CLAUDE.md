# ROSOrin Pro Autonomy Sim — Gazebo, SLAM, Nav2

Repo này chỉ chứa Phần 1 (mô phỏng ROSOrin Pro + SLAM + Nav2). Phần 2 (world models) ở repo khác, không đưa vào đây.

## Môi trường
- WSL2 (WSLg), distro `Ubuntu-22.04` (không dùng Ubuntu 24.04 mặc định của WSL), ROS 2 Humble.
- ROSOrin Pro chạy trên **Ignition Gazebo 6 (Fortress)** + `ros_gz_bridge`; TurtleBot3 baseline chạy trên Gazebo Classic 11.
- Danh sách lệnh cài đặt đầy đủ: `docs/ENVIRONMENT.md`.
- Gốc colcon = gốc repo. Code nằm trong `src/`. Build sinh `build/ install/ log/` ở gốc repo (đã gitignore).
- Mỗi terminal mới: `source /opt/ros/humble/setup.bash && source install/setup.bash`
- Mọi node trong mô phỏng chạy với `use_sim_time:=true`. Thiếu tham số này là nguyên nhân hàng đầu của lỗi TF/timestamp.
- Repo dựng từ template `athackst/vscode_ros2_workspace`. `.devcontainer/` chỉ được đổi distro, không sửa gì khác.

## Cấu trúc
```
src/
  rosorin_navigation/      # package của chúng ta (ament_python)
    rosorin_navigation/    # node Python: waypoint follower, goToPose
    config/                # waypoints.yaml, param Nav2 đã chỉnh
    launch/                # sim.launch.py, slam.launch.py (bản copy đã sửa của launch Hiwonder)
    rviz/                  # nav2_clean.rviz
  simulations/             # bản gốc ROSOrin Pro từ wiki Hiwonder (robot_gazebo, rosorin_description) — KHÔNG sửa
maps/                      # map đã lưu (.pgm + .yaml)
results/nav_runs/          # CSV log mỗi lần chạy waypoint
docs/                      # PLAN, DELIVERABLES, DEBUG_LOG, ENVIRONMENT
build.sh setup.sh test.sh  # script của template, dùng chung cho VS Code task và CI
```

## Nguồn code
- Code mô phỏng ROSOrin Pro lấy từ wiki Hiwonder (không có repo GitHub công khai):
  https://wiki.hiwonder.com/projects/rosorin-pro/en/latest/
- `src/simulations/` + `.typerc` = bản gốc (`simulations.zip`, V1.0.0 2025-05-29, sha256 trong `docs/ENVIRONMENT.md`), commit riêng với message `import: ROSOrin Pro sim from Hiwonder wiki <version/date>`.
  KHÔNG sửa trực tiếp. Cần thay đổi → copy launch/param sang `src/rosorin_navigation/` rồi sửa bản copy.
- TurtleBot3 (`turtlebot3_gazebo`, model `burger`) dùng làm baseline để kiểm tra pipeline Nav2 trước khi chuyển sang ROSOrin.
- Launch gốc của Hiwonder (`robot_gazebo worlds/room_worlds/slam/navigation.launch.py`) không chạy được nguyên trạng
  trên máy này (ISSUE-006..010). Luôn dùng bản copy trong `rosorin_navigation`; header mỗi file ghi rõ đã sửa gì.

## Lệnh chính
| Bước | Lệnh | Đã xác minh |
|---|---|---|
| Build | `colcon build --symlink-install` (hoặc `./build.sh`) | [ ] |
| Mở Gazebo | `ros2 launch rosorin_navigation sim.launch.py` (`world:=empty` cho world trống) | [x] |
| Teleop | `ros2 run teleop_twist_keyboard teleop_twist_keyboard` (bridge nối `/cmd_vel` → `/controller/cmd_vel`) | [ ] |
| Kiểm tra LiDAR | `ros2 topic hz /scan` + RViz thêm LaserScan | [x] |
| SLAM | `ros2 launch rosorin_navigation slam.launch.py` | [x] |
| Lưu map | `ros2 run nav2_map_server map_saver_cli -f maps/<map_name> --ros-args -p use_sim_time:=true` | [ ] |
| Navigation | chưa port (`robot_gazebo/launch/include/navigation.launch.py` → `rosorin_navigation`) | [ ] |
| Multi-waypoint | `ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml` | [ ] |

Khi một lệnh chạy được: chép nguyên văn vào `COMMANDS.md`, tick cột "Đã xác minh".

## Quy tắc chạy (rút ra từ DEBUG_LOG)
- Chạy Gazebo / Nav2 bringup / RViz ở **3 terminal riêng**, không dùng launch gộp (bị timeout, robot không spawn).
- Trước khi chạy lại: `pkill -f "ign gazebo"; pkill -x rviz2; pkill -f slam_toolbox` (TurtleBot3: `pkill -x gzserver; pkill -x gzclient`).
- Ignition trên WSL2: GUI phải dùng ogre (v1) và cần `MESA_GL_VERSION_OVERRIDE=4.5` — đã đặt sẵn trong `sim.launch.py`.
- `static_map_tf:=true` chỉ dùng khi KHÔNG chạy SLAM/AMCL.
- Đặt initial pose từ tọa độ thật của robot trong Gazebo (`gz model -m <model> -p`), không kéo tay "2D Pose Estimate".
- Kiểm tra GPU: `glxinfo -B | grep -i renderer` phải ra NVIDIA, không phải Intel iGPU.

## Multi-point navigation (`src/rosorin_navigation/`)
- Bắt đầu từ ví dụ chính thức `example_waypoint_follower.py` của `nav2_simple_commander` (Nav2, nhánh humble).
  Ghi nguồn ở đầu file. Không viết action client từ đầu.
- Đăng ký entry point trong `setup.py` (`console_scripts`), cài `config/`, `launch/`, `rviz/` qua `data_files`.
- Release notes: thêm mục vào `CHANGELOGS.md` mỗi khi đổi hành vi (launch, config, script).
- Waypoint đọc từ `src/rosorin_navigation/config/waypoints.yaml` (x, y, yaw theo frame `map`), không hardcode trong code.
- Log cho mỗi waypoint: thời điểm bắt đầu, kết thúc, trạng thái (SUCCEEDED/FAILED), quãng đường ước tính.
  Ghi ra `results/nav_runs/<timestamp>.csv` → số liệu cho báo cáo (tỷ lệ tới đích, thời gian).
- Single-goal: dùng "2D Goal Pose" trong RViz, hoặc `goToPose` trong cùng package.
- Code Python theo flake8 + pep257 (test có sẵn trong `src/rosorin_navigation/test/`, chạy bằng `./test.sh`).

## Quay video demo (3–5 phút, thứ tự cố định)
1. Gazebo + robot (10s) → 2. Teleop (20s) → 3. RViz LiDAR (20s) → 4. SLAM đang vẽ map (60s, có thể tua nhanh)
→ 5. Map đã lưu (10s) → 6. Single goal (40s) → 7. Multi-waypoint (60s) → 8. Tóm tắt (10s)
Quay bằng OBS trên Windows (WSLg). Không commit video; upload rồi ghi link vào `docs/VIDEOS.md`.

## Lỗi thường gặp cần kiểm tra trước khi debug sâu
- Mesh không hiện trong Gazebo → `GAZEBO_MODEL_PATH` (Gazebo Classic) hoặc `IGN_GAZEBO_RESOURCE_PATH` (Fortress).
- Mesh có texture bị đen → GUI đang dùng ogre2 (ISSUE-008).
- `Invalid frame ID "odom"` → robot chưa spawn; kiểm tra terminal Gazebo trước khi nhìn Nav2.
- Robot không định vị được trên map → chưa đặt initial pose cho AMCL, hoặc thiếu `use_sim_time`.
- Gazebo chậm (FPS thấp, RTF < 0.5) → WSL đang dùng iGPU; xem ISSUE-003 trong `docs/DEBUG_LOG.md`.
- TF thiếu `map→odom` → SLAM/AMCL chưa chạy hoặc đang chạy hai node cùng phát TF này.
- Vật cản "ma" trên costmap → initial pose sai; đặt lại pose rồi clear costmap.
Mọi lỗi thật gặp phải → `/log-issue`.

## Git
- Không thêm dòng `Co-Authored-By: Claude` hay "Generated with Claude Code" vào commit/PR.

## Agent skills

### Issue tracker

GitHub Issues của `vminh16/rosorin-autonomy-sim`, thao tác qua `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

5 nhãn mặc định: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` ở gốc repo. See `docs/agents/domain.md`.
