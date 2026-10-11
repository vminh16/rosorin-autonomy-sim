# ROSOrin Autonomy Sim

Simulation stack for the **Hiwonder ROSOrin Pro** mecanum-wheel robot: Ignition Gazebo (Fortress) simulation,
LiDAR-based SLAM, and autonomous navigation with Nav2 — single-goal and multi-waypoint missions with per-run logging.

Built on ROS 2 Humble, Ubuntu 22.04, running under WSL2 with WSLg.

![ROSOrin Pro in the robocup_home world](docs/images/gazebo_robocup_home.png)

## Features

- **Simulation** — ROSOrin Pro (mecanum drive, 2D LiDAR, depth camera) in a furnished house world; teleop via `/cmd_vel`.
- **Mapping** — 2D SLAM with `slam_toolbox`; maps saved as `.pgm` + `.yaml`.
- **Localization & navigation** — AMCL + Nav2 on a saved map; goals from RViz or from code.
- **Multi-waypoint missions** — `rosorin_navigation` node built on `nav2_simple_commander`, waypoints loaded from YAML,
  each run logged to CSV (start/end time, result, distance) for success-rate and timing analysis. *(in progress)*

## Architecture

```
 Ignition Gazebo (robot + world)
   │  ign topics ──► ros_gz_bridge ──► /scan /odom /tf /joint_states /clock /depth_cam/*
   ▲
   │ /controller/cmd_vel (bridged from ROS /cmd_vel)
   │
 teleop / Nav2 controller ◄── Nav2 (AMCL, planner, controller, costmaps) ◄── rosorin_navigation (waypoints)
                                    ▲
 SLAM (slam_toolbox) ── map→odom ───┘──► maps/<name>.yaml
```

## Repository layout

```
src/
  simulations/             # Hiwonder ROSOrin Pro sim, imported unmodified (robot_gazebo, rosorin_description)
  rosorin_navigation/      # our package: fixed launch files, RViz configs, navigation scripts
    launch/sim.launch.py   #   Gazebo + robot + ROS bridge (fixed copy of Hiwonder launches)
    launch/slam.launch.py  #   slam_toolbox + RViz with sim time
    worlds/robocup_home.sdf#   house world, 10 ms physics step
    rviz/slam.rviz         #   SLAM view, 60 fps
    rviz/nav2_clean.rviz   #   Nav2 view with robot model on, particle cloud off, 60 fps
.typerc                    # Hiwonder robot config (LiDAR / camera / chassis type), kept for reference
maps/                      # saved maps
results/nav_runs/          # navigation run logs (CSV)
docs/                      # ENVIRONMENT, DEBUG_LOG, PLAN, DELIVERABLES, images
CHANGELOGS.md
```

Upstream Hiwonder packages are never edited in place. Bugs in them are fixed in copies inside `rosorin_navigation`
(see the header of each launch file and [`docs/DEBUG_LOG.md`](docs/DEBUG_LOG.md)).

## Requirements

- Ubuntu 22.04 (native or WSL2 distro `Ubuntu-22.04`)
- ROS 2 Humble desktop, Nav2, slam_toolbox, ros_gz / ros_ign, ign_ros2_control, ros2_control
- A discrete GPU is strongly recommended under WSL2

Full step-by-step installation: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Build

```bash
git clone https://github.com/vminh16/rosorin-autonomy-sim.git ~/research/rosorin-autonomy-sim
cd ~/research/rosorin-autonomy-sim
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -y --rosdistro humble
colcon build --symlink-install
```

## Usage

Open one terminal per stage and in each run `source /opt/ros/humble/setup.bash && source install/setup.bash`
from the repo root. Start a stage only after the previous one is up.

**0. Clean up leftovers from a previous run** (a stale simulator makes the new robot fail to spawn):

```bash
pkill -f "ign gazebo"; pkill -x rviz2; pkill -f slam_toolbox
```

**1. Simulation** — Gazebo window opens, robot spawns at the house centre:

```bash
ros2 launch rosorin_navigation sim.launch.py                 # furnished house (default)
ros2 launch rosorin_navigation sim.launch.py world:=empty    # empty world
```

Useful arguments: `furniture:=false` (walls only), `camera:=false` (do not bridge the RGB camera),
`gui:=false` (server only), `x:= y:= yaw:=` (spawn pose).

**2. Teleop** — drive the robot (`i` forward, `j`/`l` turn, `k` stop; mecanum strafe with `Shift+J`/`Shift+L`):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

**3. Check the LiDAR**:

```bash
ros2 topic hz /scan
```

**4. SLAM** — opens RViz with the growing map; drive slowly around the house with teleop:

```bash
ros2 launch rosorin_navigation slam.launch.py
```

**5. Save the map**:

```bash
mkdir -p maps && ros2 run nav2_map_server map_saver_cli -f maps/house --ros-args -p use_sim_time:=true
```

**6. Navigation** *(being ported — see `COMMANDS.md` for the verified version once done)*.

Exact verified commands, with dates, are kept in [`COMMANDS.md`](COMMANDS.md).

### Waypoint file *(planned format)*

```yaml
# src/rosorin_navigation/config/waypoints.yaml — poses in the `map` frame
waypoints:
  - {x: 1.0, y: 0.0, yaw: 0.0}
  - {x: 1.0, y: 1.5, yaw: 1.57}
```

## Results

| Metric | Value |
|---|---|
| Gazebo Real Time Factor, robocup_home + SLAM + RViz (WSL2, RTX 2050) | 1.00 (was 0.50 with upstream launch) |
| `/scan` / `/odom` / camera rate | 10 Hz / 50 Hz / 27.6 Hz |
| Physics step | 10 ms (upstream 30 ms) |
| RViz frame rate during SLAM | ~57 fps (upstream config ~31 fps) |
| Waypoint success rate | _pending_ |
| Mean time per waypoint | _pending_ |

| Gazebo close-up | SLAM in RViz |
|---|---|
| ![robot](docs/images/gazebo_rosorin_closeup.png) | ![slam](docs/images/rviz_slam.png) |

Demo video: _pending_.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Furniture renders solid black | ogre2 on WSL2 D3D12 Mesa | `sim.launch.py` uses `gui_render_engine:=ogre` (default) |
| Gazebo aborts with `OGRE EXCEPTION ... GL3PlusTextureGpu::copyTo` | Mesa D3D12 reports OpenGL 4.2 | `sim.launch.py` sets `MESA_GL_VERSION_OVERRIDE=4.5` |
| `package 'holonomic_sim' not found` | Hiwonder `worlds.launch.py` / `room_worlds.launch.py` bug | use `rosorin_navigation sim.launch.py` |
| Map jumps / TF warnings with SLAM or AMCL | Hiwonder bridge always publishes static `map→odom` | off by default in `sim.launch.py` |
| Low Real Time Factor (~0.5), jerky motion in `robocup_home` | upstream furniture spawned as dynamic bodies, 30 ms physics step | `sim.launch.py` spawns furniture static, world copy uses 10 ms step (ISSUE-012) |
| RViz looks smeared while driving (Nav2 view) | AMCL particle cloud redrawn every frame, robot model hidden | `rviz2 -d src/rosorin_navigation/rviz/nav2_clean.rviz --ros-args -p use_sim_time:=true` |

Full history of issues and fixes: [`docs/DEBUG_LOG.md`](docs/DEBUG_LOG.md). Release notes: [`CHANGELOGS.md`](CHANGELOGS.md).

## Acknowledgements

- [Hiwonder ROSOrin Pro documentation](https://wiki.hiwonder.com/projects/rosorin-pro/en/latest/) — robot model and simulation packages
- [Nav2](https://docs.nav2.org/) and `nav2_simple_commander` examples
- [athackst/vscode_ros2_workspace](https://github.com/athackst/vscode_ros2_workspace) — workspace template

## License

Own code: see [`LICENSE`](LICENSE). `src/simulations/` is © Hiwonder, redistributed as published on their wiki.
