# Environment setup

Tested on **Ubuntu 22.04.5 LTS** (WSL2, and native with an NVIDIA driver) with **ROS 2 Humble**, Ignition Gazebo 6 (Fortress) for the ROSOrin Pro, Gazebo Classic 11
for the TurtleBot3 baseline, and an NVIDIA RTX 2050. Ubuntu 22.04 is required: ROS 2 Humble binaries do not exist for
24.04. The same steps work on a native install and inside a WSL2 distro; the few differences are in
[Platform notes](#6-platform-notes). Problems met during setup are logged in [`DEBUG_LOG.md`](DEBUG_LOG.md).

## 1. Quick path

```bash
# 1. Install ROS 2 Humble desktop (section 2), then:
git clone https://github.com/vminh16/rosorin-autonomy-sim.git ~/research/rosorin-autonomy-sim
cd ~/research/rosorin-autonomy-sim
source /opt/ros/humble/setup.bash
./setup.sh                          # rosdep: installs every dependency declared in the package.xml files
colcon build --symlink-install
source install/setup.bash
```

`./setup.sh` is the workspace-template script (`vcs import` of `src/ros2.repos`, which is empty here, then `rosdep install`).
Section 3 lists the same packages by name, for installing them by hand or checking what is needed.

## 2. ROS 2 Humble

Official guide: <https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html>

```bash
# UTF-8 locale
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# ROS 2 apt repository
sudo apt install -y software-properties-common curl git
sudo add-apt-repository universe
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

# ROS 2 desktop (includes RViz) and development tools (colcon, rosdep, vcstool)
sudo apt update && sudo apt upgrade -y
sudo apt install -y ros-humble-desktop ros-dev-tools

# rosdep
sudo rosdep init
rosdep update
```

## 3. Simulation, SLAM and navigation packages

```bash
# Ignition Fortress + ROS bridge (the ROSOrin Pro simulation)
sudo apt install -y ros-humble-ros-gz ros-humble-ros-ign-gazebo ros-humble-ros-ign-bridge

# Nav2, bringup and the Python API used by the waypoint follower (nav2_simple_commander)
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-simple-commander

# SLAM
sudo apt install -y ros-humble-slam-toolbox ros-humble-cartographer ros-humble-cartographer-ros

# Teleoperation, and TurtleBot3 + Gazebo Classic (baseline used to validate the Nav2 pipeline)
sudo apt install -y ros-humble-teleop-twist-keyboard ros-humble-gazebo-ros-pkgs ros-humble-turtlebot3-gazebo

# GPU check (glxinfo)
sudo apt install -y mesa-utils
```

`ros-humble-ign-ros2-control`, `ros-humble-ros2-control` and `ros-humble-ros2-controllers` are declared or referenced by the
Hiwonder package but are not used by the launch files of this repository.

Versions installed when this document was written (`dpkg -l`):

| Package | Version |
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
| ignition gazebo (Fortress) | 6.18.0 |

## 4. Environment variables

Add to `~/.bashrc` (only needed for the TurtleBot3 baseline):

```bash
source /opt/ros/humble/setup.bash
source /usr/share/gazebo/setup.sh                 # Gazebo Classic model and plugin paths
export TURTLEBOT3_MODEL=burger                    # lighter than waffle
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models
```

Do not build or run inside a conda environment (`conda deactivate`, and `conda config --set auto_activate false`
if conda is installed; `auto_activate_base` on conda older than 25): `which python3` must print `/usr/bin/python3`, otherwise colcon and the launch files pick up conda's
Python, which has no `rclpy`, `catkin_pkg` or `em`. If the desktop language is not English, numbers may be formatted with a
decimal comma (`locale | grep LC_NUMERIC` shows e.g. `vi_VN`); add `export LC_NUMERIC=en_US.UTF-8` to `~/.bashrc` so that
every ROS and Gazebo tool parses `0.08` as a number.

Source the workspace by hand in every terminal after a build (not from `.bashrc`, to avoid sourcing a stale build):

```bash
cd ~/research/rosorin-autonomy-sim && source /opt/ros/humble/setup.bash && source install/setup.bash
```

`sim.launch.py` sets what the ROSOrin simulation needs, so nothing else has to be exported:
`DEPTH_CAMERA_TYPE=aurora` (read by the Hiwonder xacro, default taken from `.typerc`) and `MESA_GL_VERSION_OVERRIDE=4.5`
(see platform notes). Do not `source .typerc`: it also sets `ROS_DOMAIN_ID` and a `CYCLONEDDS_URI` that points to a file that does
not exist on this machine.

## 5. Vendor simulation source

The ROSOrin Pro simulation has no public git repository. It comes from the Hiwonder wiki, section 9.2.1 (Google Drive folder
"3. Feature Package"): <https://drive.google.com/drive/folders/1sq3698U-EX7a4gbjmGnwYbptlJ3B8aMM>. It is already in this
repository, unmodified:

| File | Location | sha256 |
|---|---|---|
| `simulations.zip` | `src/simulations/` | `a4d23a901dd24472cfdb4655304fd4409bdb5982a7ebdea13f70ec42aef8dad2` |
| `.typerc` | `.typerc` | `0c1f9c4b256beed7a1e1ffefcb3149577fcf6730284f1cbc2bbf2c09adee6320` |

## 6. Platform notes

Hybrid-GPU laptops (Intel + NVIDIA, `prime-select query` prints `on-demand`): applications render on the Intel GPU by
default. The simulation works there, but to use the NVIDIA GPU start it with PRIME offload (checked with `nvidia-smi`, which then
lists `ign gazebo server` and `ign gazebo gui`):

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ros2 launch rosorin_navigation sim.launch.py
```

Differences that matter on **WSL2 (WSLg)**; none of them applies to a native Ubuntu install.

| Topic | What to do | Why |
|---|---|---|
| Distro | `wsl --install -d Ubuntu-22.04` | the default distro is 24.04, which has no Humble packages (ISSUE-001) |
| Memory | `%UserProfile%\.wslconfig`: `[wsl2]` `memory=8GB` (12GB and `processors=6` used here), then `wsl --shutdown` | the default allocation was too small (ISSUE-003) |
| GPU | `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` in `~/.bashrc`; check with `glxinfo -B \| grep -i renderer` | WSLg picked the integrated Intel GPU: 5.8 FPS instead of 61 (ISSUE-003) |
| OpenGL version | handled by `sim.launch.py` (`MESA_GL_VERSION_OVERRIDE=4.5`) | Mesa D3D12 reports OpenGL 4.2 and ogre2 aborts (ISSUE-007) |
| GUI render engine | handled by `sim.launch.py` (`gui_render_engine:=ogre`) | ogre2 renders textured meshes black on Mesa D3D12 (ISSUE-008) |

## 7. Smoke test

```bash
printenv ROS_DISTRO                                   # humble
ros2 pkg list | grep -E 'nav2_bringup|slam_toolbox|ros_gz_bridge|robot_gazebo|rosorin_navigation'
python3 -m pytest src/rosorin_navigation/test/test_sim_fidelity.py -q    # 13 passed, no simulator needed
ros2 launch rosorin_navigation sim.launch.py          # Gazebo opens, the ROSOrin appears in the house
```

## 8. Clean rebuild

If a build or launch fails after switching branches, moving the repository, or mixing build commands, delete the build
artifacts and start again. They are generated files only (ignored by git); nothing in `src/` is touched.

```bash
cd ~/research/rosorin-autonomy-sim
pkill -f "ign gazebo"; pkill -x rviz2; pkill -f parameter_bridge   # stop any running simulation
conda deactivate 2>/dev/null; which python3                         # must be /usr/bin/python3
rm -rf build install log                                            # build artifacts only
source /opt/ros/humble/setup.bash
./setup.sh                                                          # re-check the dependencies
colcon build --symlink-install                                      # or ./build.sh (same layout)
source install/setup.bash                                           # in EVERY new terminal
python3 -m pytest src/rosorin_navigation/test/test_sim_fidelity.py -q
ros2 launch rosorin_navigation sim.launch.py
```

Typical errors and their cause:

| Error | Cause |
|---|---|
| `Package 'rosorin_navigation' not found` | `install/setup.bash` not sourced in this terminal |
| `The install directory 'install' was created with the layout 'merged'` | an older `build.sh` used `--merge-install`; `rm -rf build install log` and rebuild |
| `ROS_DISTRO is not set` from `./setup.sh` | `/opt/ros/humble/setup.bash` not sourced |
| `ModuleNotFoundError: No module named 'catkin_pkg'` / `'em'` / `'rclpy'` | a conda environment is active |
| `./test.sh` shows flake8 failures in `robot_gazebo` / `rosorin_description` | plain `colcon test` also tests the vendored Hiwonder code; `./test.sh` tests only this project's packages (24 tests) |
