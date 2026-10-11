# Environment Setup

Môi trường đã dùng cho repo này: Windows + WSL2 (WSLg), **Ubuntu 22.04.5 LTS**, **ROS 2 Humble**, Ignition Gazebo 6 (Fortress) cho ROSOrin Pro, Gazebo Classic 11 cho baseline TurtleBot3, GPU NVIDIA RTX 2050.
Làm theo thứ tự từ trên xuống. Các lỗi gặp khi cài được ghi trong [`DEBUG_LOG.md`](DEBUG_LOG.md).

## 1. WSL2 + Ubuntu 22.04 (PowerShell trên Windows)

```powershell
wsl --install -d Ubuntu-22.04      # KHÔNG dùng distro mặc định (24.04) — xem ISSUE-001
wsl --set-default Ubuntu-22.04
```

Cấp RAM/CPU cho WSL trong `%UserProfile%\.wslconfig` (tối thiểu `memory=8GB`, xem ISSUE-003). Cấu hình hiện tại:

```ini
[wsl2]
memory=12GB
processors=6
```

Áp dụng: `wsl --shutdown`, rồi mở lại terminal Ubuntu.

## 2. ROS 2 Humble

Theo hướng dẫn chính thức: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html

```bash
# Locale UTF-8
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Repo ROS 2
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

# ROS 2 desktop (gồm RViz) + công cụ dev (colcon, rosdep, vcstool)
sudo apt update && sudo apt upgrade -y
sudo apt install -y ros-humble-desktop ros-dev-tools

# rosdep
sudo rosdep init
rosdep update
```

## 3. Gói mô phỏng, SLAM, điều hướng

```bash
# Gazebo Classic 11 + bridge ROS (gazebo_ros_pkgs)
sudo apt install -y ros-humble-gazebo-ros-pkgs

# Gazebo mới (Ignition Fortress) + bridge ros_gz — dùng nếu package Hiwonder yêu cầu
sudo apt install -y ros-humble-ros-gz

# Nav2 + bringup + Python API (nav2_simple_commander, dùng cho waypoint follower)
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-simple-commander

# SLAM
sudo apt install -y ros-humble-slam-toolbox
sudo apt install -y ros-humble-cartographer ros-humble-cartographer-ros

# Teleop + TurtleBot3 (baseline kiểm thử pipeline)
sudo apt install -y ros-humble-teleop-twist-keyboard ros-humble-turtlebot3-gazebo

# Kiểm tra GPU trong WSL
sudo apt install -y mesa-utils

# ROSOrin Pro (Hiwonder, src/simulations): bridge/launch tên cũ ros_ign_*, ign_ros2_control, ros2_control
sudo apt install -y ros-humble-ros-ign-gazebo ros-humble-ros-ign-bridge ros-humble-ign-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers
```

Ba gói `ros_ign_*` / `ign_ros2_control` là những gói `rosdep` báo thiếu cho `robot_gazebo`. `ros2_control` +
`ros2_controllers` không được khai báo trong `package.xml` của Hiwonder nhưng launch gốc gọi `controller_manager`.

Phiên bản đã cài lúc ghi tài liệu (`dpkg -l`):

| Gói | Phiên bản |
|---|---|
| ros-humble-desktop | 0.10.0 |
| ros-humble-navigation2 / nav2-bringup / nav2-simple-commander | 1.1.20 |
| ros-humble-slam-toolbox | 2.6.10 |
| ros-humble-cartographer / cartographer-ros | 2.0.9004 / 2.0.9002 |
| ros-humble-gazebo-ros-pkgs | 3.9.0 |
| gazebo (Classic) | 11.10.2 |
| ros-humble-ros-gz | 0.244.26 |
| ros-humble-turtlebot3-gazebo | 2.3.8 |
| ros-humble-teleop-twist-keyboard | 2.4.1 |
| ros-humble-ros2-controllers | 2.54.0 |
| ignition gazebo (Fortress) | 6.18.0 |

## 4. Biến môi trường (`~/.bashrc`)

```bash
source /opt/ros/humble/setup.bash
source /usr/share/gazebo/setup.sh                 # Gazebo Classic: GAZEBO_MODEL_PATH, plugin path
export TURTLEBOT3_MODEL=burger                    # burger nhẹ hơn waffle (ISSUE-003)
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA     # WSLg render bằng GPU NVIDIA thay vì iGPU Intel (ISSUE-003)
```

Không cần đặt trong `.bashrc` (đã có sẵn trong `rosorin_navigation/launch/sim.launch.py`):
- `MESA_GL_VERSION_OVERRIDE=4.5`: Mesa D3D12 chỉ báo OpenGL 4.2, ogre2 crash nếu thiếu (ISSUE-007).
- `DEPTH_CAMERA_TYPE=aurora`: xacro của Hiwonder đọc biến này; giá trị lấy từ `.typerc`.

`.typerc` (của Hiwonder) được giữ ở gốc repo để tham khảo, **không cần source**: nó còn đặt `ROS_DOMAIN_ID=0`
và `CYCLONEDDS_URI` trỏ tới file không tồn tại trên máy này.

Workspace của repo (source thủ công ở mỗi terminal sau khi build, không đặt trong `.bashrc` để tránh source bản build cũ):

```bash
cd ~/research/rosorin-autonomy-sim
source install/setup.bash
```

## 5. Build workspace

```bash
cd ~/research/rosorin-autonomy-sim
rosdep install --from-paths src --ignore-src -y --rosdistro humble
colcon build --symlink-install
source install/setup.bash
```

## 6. Code mô phỏng ROSOrin Pro (đã có trong repo)

Nguồn: wiki Hiwonder mục 9.2.1, thư mục Google Drive "3. Feature Package":
https://drive.google.com/drive/folders/1sq3698U-EX7a4gbjmGnwYbptlJ3B8aMM

| File | sha256 |
|---|---|
| `simulations.zip` → `src/simulations/` | `a4d23a901dd24472cfdb4655304fd4409bdb5982a7ebdea13f70ec42aef8dad2` |
| `.typerc` → `.typerc` | `0c1f9c4b256beed7a1e1ffefcb3149577fcf6730284f1cbc2bbf2c09adee6320` |

## 7. Kiểm tra nhanh

```bash
printenv ROS_DISTRO                     # humble
glxinfo -B | grep -i renderer           # phải có NVIDIA
ros2 pkg list | grep -E 'nav2_bringup|slam_toolbox|ros_ign_gazebo|ros_gz_bridge|ign_ros2_control|robot_gazebo'
ros2 launch rosorin_navigation sim.launch.py                # Gazebo mở, robot ROSOrin xuất hiện giữa nhà
```
