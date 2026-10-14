# Environment setup

Tested on **Ubuntu 22.04.5 LTS** with **ROS 2 Humble** and Ignition Gazebo 6 (Fortress): natively with an NVIDIA RTX 2050
(hybrid Intel + NVIDIA laptop) and inside WSL2. Ubuntu 22.04 is required: ROS 2 Humble has no binaries for 24.04.
Problems met during setup are logged in [`DEBUG_LOG.md`](DEBUG_LOG.md).

Follow the steps in order. Steps 1 and 2 are done once per machine; step 3 is the whole workspace install.

## Step 1. Prepare the shell

Do not install or build inside a conda environment: colcon and the launch files would pick up conda's Python, which has no
`rclpy`, `catkin_pkg` or `em`.

```bash
conda deactivate 2>/dev/null; conda config --set auto_activate false 2>/dev/null   # only if conda is installed
which python3                                                                        # must print /usr/bin/python3
```

If the desktop language is not English, numbers may be printed with a decimal comma (`locale | grep LC_NUMERIC` shows e.g.
`vi_VN`), and some ROS and Gazebo tools then misread `0.08`. Fix it once:

```bash
echo 'export LC_NUMERIC=en_US.UTF-8' >> ~/.bashrc && source ~/.bashrc
```

## Step 2. Install ROS 2 Humble

Official guide: <https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html>. The same commands:

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

# ROS 2 desktop (includes RViz) and the development tools (colcon, rosdep, vcstool)
sudo apt update && sudo apt upgrade -y
sudo apt install -y ros-humble-desktop ros-dev-tools

# rosdep, once per machine
sudo rosdep init
rosdep update
```

## Step 3. Install, build and test the workspace

```bash
git clone https://github.com/vminh16/rosorin-autonomy-sim.git
cd rosorin-autonomy-sim
source /opt/ros/humble/setup.bash
./setup.sh                  # 3a. installs the packages below, then rosdep
./build.sh                  # 3b. colcon build --symlink-install (4 packages)
source install/setup.bash   # 3c. in every new terminal, after every build
./test.sh                   # 3d. 27 tests, 0 failures, no simulator needed
ros2 launch rosorin_navigation sim.launch.py   # 3e. Gazebo opens, the robot appears in the house
```

`./setup.sh` checks the shell (ROS sourced, no conda), installs these packages with apt, then runs `rosdep install` for the
rest of the dependencies declared in the `package.xml` files:

| Packages | Used for |
|---|---|
| `ros-humble-ros-gz-sim`, `ros-gz-bridge`, `ros-ign-gazebo`, `ros-ign-bridge` | Ignition Gazebo Fortress and the ROS bridge |
| `ros-humble-navigation2`, `nav2-bringup`, `nav2-simple-commander` | Nav2 and the Python API of the waypoint follower |
| `ros-humble-slam-toolbox` | SLAM |
| `ros-humble-robot-localization` | EKF of `sim.launch.py realism:=true` (wheel odometry + IMU, as on the real robot) |
| `ros-humble-teleop-twist-keyboard` | keyboard driving |
| `ros-humble-xacro`, `robot-state-publisher` | robot model |
| `python3-numpy`, `python3-yaml`, `python3-pytest` | nodes and tests |

Source the workspace by hand in each terminal (not from `~/.bashrc`, to avoid sourcing a stale build):

```bash
cd ~/rosorin-autonomy-sim && source /opt/ros/humble/setup.bash && source install/setup.bash
```

`sim.launch.py` sets what the simulation needs, so nothing else has to be exported: `DEPTH_CAMERA_TYPE=aurora` (read by
the Hiwonder xacro), and on WSL2 only `MESA_GL_VERSION_OVERRIDE=4.5` with the ogre (v1) GUI. Do not `source .typerc`: it also
sets a `ROS_DOMAIN_ID` and a `CYCLONEDDS_URI` pointing to a file that does not exist here.

Versions installed when this document was written (`dpkg -l`):

| Package | Version |
|---|---|
| ros-humble-desktop | 0.10.0 |
| ros-humble-navigation2 / nav2-bringup / nav2-simple-commander | 1.1.20 |
| ros-humble-slam-toolbox | 2.6.10 |
| ros-humble-robot-localization | 3.5.4 |
| ros-humble-ros-gz-sim | 0.244.26 |
| ros-humble-teleop-twist-keyboard | 2.4.1 |
| ignition gazebo (Fortress) | 6.18.0 |

Optional, only for the TurtleBot3 baseline used early on to validate Nav2 (Gazebo Classic, see `COMMANDS.md`):

```bash
sudo apt install -y ros-humble-gazebo-ros-pkgs ros-humble-turtlebot3-gazebo ros-humble-cartographer-ros
export TURTLEBOT3_MODEL=burger
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models
```

## Clean rebuild

If a build or launch fails after switching branches, moving the repository or mixing build commands, delete the build
artifacts (generated files only, ignored by git) and repeat step 3:

```bash
pkill -f "ign gazebo"; pkill -x rviz2; pkill -f parameter_bridge   # stop any running simulation
rm -rf build install log
source /opt/ros/humble/setup.bash && ./setup.sh && ./build.sh && source install/setup.bash && ./test.sh
```

| Error | Cause |
|---|---|
| `Package 'rosorin_navigation' not found` | `install/setup.bash` not sourced in this terminal |
| `The install directory 'install' was created with the layout 'merged'` | built earlier with `--merge-install`; clean rebuild |
| `ROS_DISTRO is not set` from `./setup.sh` | `/opt/ros/humble/setup.bash` not sourced |
| `ModuleNotFoundError: No module named 'catkin_pkg'` / `'em'` / `'rclpy'` | a conda environment is active (step 1) |
| `realism:=true needs robot_localization` | `./setup.sh` not run since the package was added |
| flake8 failures in `robot_gazebo` / `rosorin_description` | plain `colcon test` also tests the vendored Hiwonder code; use `./test.sh` |

## Platform notes

**Hybrid-GPU laptops** (Intel + NVIDIA, `prime-select query` prints `on-demand`): applications render on the Intel GPU by
default. The simulation works there; to use the NVIDIA GPU, start it with PRIME offload (`nvidia-smi` then lists
`ign gazebo`):

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ros2 launch rosorin_navigation sim.launch.py
```

**WSL2 (WSLg)**; none of this applies to a native install:

| Topic | What to do | Why |
|---|---|---|
| Distro | `wsl --install -d Ubuntu-22.04` | the default distro is 24.04, which has no Humble packages (ISSUE-001) |
| Memory | `%UserProfile%\.wslconfig`: `[wsl2]` `memory=8GB`, then `wsl --shutdown` | the default allocation was too small (ISSUE-003) |
| GPU | `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` in `~/.bashrc`; check with `glxinfo -B \| grep -i renderer` (`mesa-utils`) | WSLg picked the integrated GPU: 5.8 FPS instead of 61 (ISSUE-003) |
| OpenGL, GUI engine | nothing: `sim.launch.py` detects WSL2, sets `MESA_GL_VERSION_OVERRIDE=4.5` and uses the ogre GUI | Mesa D3D12 reports OpenGL 4.2 and ogre2 aborts or draws meshes black (ISSUE-007, ISSUE-008) |

## Vendor simulation source

The ROSOrin Pro simulation has no public git repository. It comes from the Hiwonder wiki, section 9.2.1 (Google Drive folder
"3. Feature Package"): <https://drive.google.com/drive/folders/1sq3698U-EX7a4gbjmGnwYbptlJ3B8aMM>. It is already in this
repository, unmodified (only a stray vim swap file, `.ros_ign_bridge.launch.py.swp`, was removed):

| File | Location | sha256 |
|---|---|---|
| `simulations.zip` | `src/simulations/` | `a4d23a901dd24472cfdb4655304fd4409bdb5982a7ebdea13f70ec42aef8dad2` |
| `.typerc` | `.typerc` | `0c1f9c4b256beed7a1e1ffefcb3149577fcf6730284f1cbc2bbf2c09adee6320` |
