# Debug Log

Raw source for the "problems encountered and solutions" part of the report ([`../report/report.md`](../report/report.md)).
Newest entries first. Each entry records the command, the error, the cause (marked as verified or as a hypothesis) and the fix.

<!--
Entry template:

## ISSUE-NNN — <short title>
- Date: YYYY-MM-DD
- Component: Env | Gazebo | SLAM | Nav2 | rosorin_navigation | Build/CI
- Status: OPEN | FIXED | WORKAROUND | WONTFIX
- Command that fails:
  ```bash
  <exact command>
  ```
- Error (the most important lines only, not the whole log):
  ```
  <message>
  ```
- Cause: <verified, or "hypothesis:">
- Fix: <what changed: file, line, version, command>
- Time spent: <hours>
- In report: yes | no
-->

## ISSUE-018 — DWB stalls on a U-shaped path: "Failed to make progress" next to the dining tables
- Date: 2026-10-12
- Component: Nav2
- Status: FIXED
- Command that fails: headless `sim.launch.py gui:=false` + `navigation.launch.py rviz:=false` (vendor DWB parameters,
  `config/nav2_params.yaml`), goals sent with `nav2_simple_commander`; goal (3.0, -1.5, 3.14) after goal (4.0, 2.0, -1.57)
- Error: fails 3 of 3 runs. The robot stops at about (1.94, 0.35) in the corridor between the dining chairs and the bookshelf
  wall, recoveries (clear costmap, spin, wait, back up) repeat until the 180 s timeout:
  ```
  [controller_server]: Failed to make progress
  [controller_server]: [follow_path] [ActionServer] Aborting handle.
  ```
  The other 5 goals of the same run succeed.
- Cause (verified from `/cmd_vel_nav`, `/odom` and DWB `/evaluation`): the robot is not blocked, the controller itself
  commands `vx = 0`, `wz = +-0.053`. The global path is U-shaped: west 1.4 m along the corridor, around the end of the wall,
  then east to the goal behind the wall. The whole U fits inside the 2 m window that DWB keeps of the plan (half of the 4 m
  local costmap), so the local goal is the real goal, south-east behind the wall. GoalDist + GoalAlign (24 each, about 66 of a
  total of 67) then reward facing the wall (south), PathAlign/PathDist (32 each) reward facing the path (west). Example scores:
  best `vx 0, wz +0.05` = 67.4; turning to the path direction `wz -1.0` = 68.4 (PathAlign -0.8, GoalAlign +1.8); driving
  forward costs more than 70. DWB picks a near-zero rotation forever. Free running elsewhere is fine.
- Fix: local controller MPPI (Nav2 Humble 1.1.20 binary, `DiffDrive`, 0.4 m/s, 1.0 rad/s, no sideways
  motion, critics from the Nav2 MPPI documentation) instead of DWB. TEB, the real robot's default, has no Humble binary and
  the vendor did not ship its YAML. Same 6 goals on a clean machine, true final pose from Gazebo: DWB 5/6, MPPI 6/6 (the
  failing goal in 31.5 s over 8.1 m). Also fixed in the same file: `velocity_smoother` clipped to 0.26 m/s while the controller
  planned with 0.4 m/s.
- Time spent: 1.5 h
- In report: yes

## ISSUE-017 — The simulated robot drives faster than its motors allow
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `python3 tools/probe_physics.py` (empty world)
- Error: `top vx FAIL command 1.0 -> steady 1.000 (wheel-speed limit 0.461)`; same for vy (1.000) and wz (5.000 rad/s, limit 2.643).
- Cause (verified): PlanarDrive tracked any command. The real motors run at most 110 rpm no-load at the output shaft (wiki
  1.10.2.3, 1:90 gearbox), so with the 0.08 m wheel (2.2.2.4) a wheel reaches 0.461 m/s and the robot turns at most 2.64 rad/s.
  The wiki's "recommended range -0.6 ~ 0.6 m/s" (2.1.5.2) is above this physical limit.
- Fix (`6916228`): PlanarDrive scales the command so that the fastest mecanum wheel, (|vx| + |vy| + k|wz|) / r, stays at or
  below `max_wheel_speed` = 11.519 rad/s. Results: top speed 0.461 m/s forward and sideways, 2.643 rad/s turning; the other
  probe cases unchanged (rest: no creep or tilt; IMU at rest 9.800 m/s2, gyro 0; step 0 -> 0.3 m/s: 63 % after 0.108 s,
  max 1.77 m/s2; stop within 0.34 s); `probe_motion.py` 1.00 / 1.00 / 1.00; `probe_collision.py` 9/9.
- Limitation: no-load speed is an upper bound; under load and at 11.1 V battery the real top speed is lower (rated 85 rpm gives
  0.356 m/s).
- Time spent: —
- In report: yes

## ISSUE-016 — The robot climbs furniture, flips and flies away; `/odom` has two publishers
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: teleop during mapping (last command `linear.x = -1.0`), reproduced with
  `python3 tools/probe_collision.py` (furnished house, 1 m/s into walls and furniture, then reverse / turn / strafe while pinned)
- Error: in the user's session the robot was at z = 56 m, upside down (quaternion x 0.93, w -0.03), rising at a constant
  1.1 m/s with `/imu` reading about zero acceleration; the LiDAR then looked over the walls ("scans through walls") and the map
  was ruined. `probe_collision.py` on that model: 4 of 9 cases FAIL, tilt up to 41 deg, one case reaches z = 1.73 m.
- Cause (verified by reproduction in a separate headless simulation): introduced by my ISSUE-014 fix, not by the vendor.
  `VelocityControl` overwrites the whole body velocity every step with the command expressed in the body frame:
  1. driven into an obstacle it pushes with unlimited force, so it rides up furniture and stays wedged at about 42 deg roll /
     36 deg pitch (at 1 m/s after 4 s; at 0.25 m/s the tilt starts after about 15 s);
  2. the angular velocity is overwritten too, so the tilt never relaxes, and the body-frame command "reverse 1 m/s" now points
     upwards; gravity cannot act on an overwritten velocity, so the robot flies off (z 0 -> 0.69 -> 1.25 m in 2 s).
  A robot that starts tilted on flat ground (up to 30 deg) settles normally, so the trigger is the unlimited push. A real robot
  stops or slips its wheels: the drive force is limited by traction, about mu m g = 18 N for 3.1 kg.
  Found on the way: `MecanumDrive` also published `/odom` (wheel odometry of the free-spinning wheels) next to
  `OdometryPublisher`, so `/odom` interleaved two sources that disagree as soon as the robot is blocked
  (`ign topic -i -t /odom`: 2 publishers).
  "Scans through walls" checked separately with the robot upright: of 400 beams, the only ones without a return leave the house
  through the two known wall openings (top wall x 2.62-3.61, left wall y -1.0 to -0.8); none crosses a wall.
- Fix: new package `rosorin_gazebo_plugins` with the system `rosorin::PlanarDrive`, replacing `VelocityControl`: a horizontal
  force `m (v_cmd - v) / tau` and a yaw torque, capped at `mu m g` (mu 0.6, tau 0.1 s) and at `mu m g * lever_arm`, applied at
  the centre of mass; z, roll and pitch are left to the physics engine; no drive above 0.5 rad tilt (wheels off the ground).
  `MecanumDrive` odometry moved to `/model/rosorin/wheel_odom` (not bridged). `test_sim_fidelity.py` gains two static checks
  (no `VelocityControl`, one `/odom` publisher), both red on the old URDF. Results: `probe_collision.py` 9/9 PASS, max tilt
  0.6 deg, max z 0.003 m; `probe_motion.py` 1.00 / 1.00 / 1.00; one `/odom` publisher.
  Also fixed: `rosorin_navigation/package.xml` did not declare `rosorin_description`, which its URDF includes, so `colcon test`
  failed outside a sourced workspace.
- Lesson: ISSUE-014 was validated only on the cases I thought of (free motion, a head-on wall at 0.6 m/s, static tilt). A drive
  model has to be tested against contact, at speeds above normal use, and in sequences (pinned, then another command).
- Time spent: —
- In report: yes

## ISSUE-015 — Sensors and mass of the simulation differ from the real robot in the wiki
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `python3 -m pytest src/rosorin_navigation/test/test_sim_fidelity.py -q` (URDF against `config/wiki_reference.yaml`)
- Error: 9 of 10 checks fail on the vendor URDF:
  ```
  LiDAR FOV 156.1 deg (wiki 360), resolution 0.58 deg (wiki 0.9), camera hfov 60 deg (74), camera 30 Hz (12),
  imu_present False, plugin wheel_radius 0.05 (0.04), total mass 40.4 kg
  ```
- Cause (verified by the tests and by reading the wiki): the Hiwonder URDF declares a LiDAR with 270 beams over +-1.36263 rad.
  The wiki's own Gazebo chapter shows the same values, so the simulation matches the vendor's simulation but not the COIN-D6
  hardware (360 deg, 0.9 deg, 10 Hz, 12 m, wiki 1.10.5). The Aurora930 camera is 74x51 deg at 12 fps (wiki 1.10.4). The IMU
  plugin is loaded but no sensor is declared (ISSUE-011). The 40.4 kg come from four 10 kg wheels, while the CAD body weighs 0.4 kg.
- Fix (copy in `rosorin_navigation`, upstream untouched): `urdf/rosorin_sim.urdf.xacro`, `lidar.gazebo.xacro` (360 deg, 400 beams),
  `camera.gazebo.xacro` (74 deg, 12 Hz), IMU included, wheels 0.07 kg, a 2.4 kg ballast link for a total of about 3.1 kg (this
  figure comes from a retail listing; the wiki gives no mass). After the fix: 10/10 checks pass; `/scan` 9.95 Hz with 400 beams
  (angle increment 0.0157 rad); `/imu` 49.5 Hz, frame `imu_link`; camera 12.05 Hz (measured in simulation time).
- Still different from the real robot: RGB stream only (no depth/IR); the camera is on the chassis (real: on the arm wrist); no arm;
  `/odom` is the true physics pose (no drift or noise) while the real robot uses encoders + EKF.
- Time spent: —
- In report: yes

## ISSUE-014 — Cylinder wheels cannot emulate mecanum rollers: directional friction either blocks sideways motion or makes turning jerky
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `python3 tools/probe_motion.py --speed 0.2 --turn 0.5 --seconds 4` (simulation with `gui:=false world:=empty`)
- Error: after fixing the plugin constants (ISSUE-013) forward motion is exact (1.00) but sideways motion and turning are not.
- Cause (verified by measurement): the wheels have no 45 deg rollers, only friction direction can imitate them. With isotropic
  friction (upstream mu = 10) the wheels cannot slide sideways, so the robot cannot strafe. Directional friction (`fdir1`) is a
  trade-off. Achieved / commanded velocity, median of two runs unless a range is given:

  | friction along roller axis / across / wheel mass | sideways | turning |
  |---|---|---|
  | 0.01 / 1.5 / 0.07 kg | 0.77 once, jerky trace | 7.4 (spikes to 3.8 rad/s) |
  | 0.2 / 1.5 / 0.07 kg | 0.06 | 1.07 |
  | 0.5 / 1.0 / 0.07 kg | 0.02 | 1.03 |
  | 0.05 / 1.0 / 0.3 kg | 0.00 | 1.26-1.84 |
  | 0.01 / 1.5 / 0.5 kg | 0.00 | 2.64-2.79 |
  | Recipe of the gz-sim example `mecanum_drive.sdf` (sphere wheels, `fdir1` fixed to the chassis, mu 1.0 / mu2 0.0), 0.07 kg | 0.23-0.64 (3 runs) | 0.59-0.98 |
  | Same, roller pattern mirrored | 0.00-0.47 | 0.64-2.13 |
  | Same, 0.5 kg wheels | 0.00-0.58 | 0.82-1.31 |
  | **`VelocityControl` + frictionless wheels** | **1.00** | **1.00** |

  Forward motion is 1.00 in every physical variant. My first attempts put `fdir1` in the wheel's own frame (it rotates with the
  wheel), which is not the official recipe; the last three variants fix that and are still unstable.
- Fix: the `VelocityControl` plugin moves the body with the commanded `Twist` in the body frame (the real robot's wheel controller
  tracks the command, calibration factors 1.0 in wiki 2.1.5.5); `MecanumDrive` still spins the wheels with the wiki formula and the
  frictionless wheels only carry the weight. Checks: forward, sideways and turning all 1.00 in two runs; wheel speeds while driving
  (vx 0.3, wz 0.2) are 6.63 / 8.37 rad/s, matching `(vx -/+ wz*k)/r` with k = 0.174355 and r = 0.04; odometry velocity is zero after a
  stop command; driving into a wall at 0.6 m/s stops at x = 4.92 (wall at 5.1), no tunnelling, no tilt; RTF 1.000 in `robocup_home`
  with all furniture.
- Limitation: no wheel slip and no drivetrain dynamics of the real robot.
- Superseded: `VelocityControl` pushes with unlimited force and makes the robot climb and fly off; replaced by the
  traction-limited `PlanarDrive` (ISSUE-016).
- Time spent: —
- In report: yes

## ISSUE-013 — Hiwonder MecanumDrive constants disagree with the wheels and the wiki: 0.8x speed, 1.5x turning, no sideways motion
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `python3 tools/probe_motion.py --speed 0.2 --turn 0.5` on the vendor URDF
- Error: a 0.2 m/s command gives a steady 0.160 m/s (ratio 0.80); 0.2 m/s sideways gives 0.000; 0.5 rad/s turning oscillates 0.3-1.1 rad/s.
- Cause (verified; predicted before measuring): the plugin declares `wheel_radius` 0.05, `wheel_separation` 0.34, `wheelbase` 0.30
  (`robot.gazebo.xacro:62-64`) while the simulated wheels have radius 0.04 and are 0.16 x 0.18 m apart (`wheel.xacro:5,51-54`). The wiki
  (2.2.2.4, `mecanum.py`, the code that runs on the real robot) uses a wheel diameter of 0.08 m, `wheelbase` 0.17706 and `track_width`
  0.17165 (lever arm (a+b)/2 = 0.174355 m). 0.04 / 0.05 = 0.80 matches the measured ratio. Note: the simulation publishes the true pose
  as `/odom`, so this error is invisible in the odometry.
- Fix: plugin constants 0.04 / 0.17706 / 0.17165; wheel positions from the CAD (front-rear 0.17165 m) and the wiki (left-right
  0.17706 m). Sideways motion and turning: see ISSUE-014.
- Time spent: —
- In report: yes

## ISSUE-012 — ROSOrin real-time factor only 0.5-0.95, jerky motion
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `ros2 launch rosorin_navigation sim.launch.py`
- Error: `ign topic -e -t /stats` gives an average `real_time_factor` of 0.50; `/scan` is configured at 10 Hz but runs at about 5 Hz;
  `/odom` runs at 20 Hz.
- Cause (verified by measuring each variant, RTF averaged over 60 samples):

  | Variant | RTF |
  |---|---|
  | Default (Hiwonder) | 0.50 |
  | No GUI | 0.39 |
  | No camera bridge | 0.68 |
  | No shadows | 0.54 |
  | Physics step 0.01 s (dynamic furniture) | 0.19 |
  | `empty` world | 1.00 |
  | `robocup_home` without furniture | 1.00 |
  | **Furniture spawned as static models** | **1.00** |

  The first hypothesis (camera rendering / ogre2) was **wrong**. The cost per physics step is a fixed ~50 ms because
  `spawn_objects.launch.py` spawns 17 furniture items as dynamic bodies (none of the models has `<static>`), resting on the floor and
  on each other (bottles on a table), so the contact solver works on every step. The world's 0.03 s step hid part of the problem but
  limited the motion update to 33 times per second.
- Fix (`rosorin_navigation`):
  1. `sim.launch.py` spawns the furniture itself (positions copied from `spawn_objects.launch.py`) with `create -string`, adds
     `<gazebo><static>true</static></gazebo>` and turns relative mesh paths into absolute ones.
  2. `worlds/robocup_home.sdf`: `max_step_size` 0.03 -> 0.01 s.
  3. `rviz/slam.rviz`, `rviz/nav2_clean.rviz`: `Frame Rate` 30 -> 60.
- Result, measured with GUI + SLAM + RViz + robot running: average RTF 1.000, minimum 1.000; `/scan` 10.0 Hz; `/odom` 50 Hz;
  camera 27.6 Hz; RViz 57 fps (was 31); total CPU about 52%.
- Time spent: 1 h
- In report: yes

## ISSUE-011 — The ROSOrin IMU publishes no data
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails: `ros2 topic hz /imu`
- Error: the topic `/imu` exists (created by the bridge) but carries no message; `ign topic -l` lists no IMU topic.
- Cause (verified): Hiwonder's `robot.gazebo.xacro` loads the `Imu` system (line 35) but never includes `imu.gazebo.xacro`, so there
  is no IMU sensor.
- Fix: the copy `urdf/rosorin_sim.urdf.xacro` includes Hiwonder's `imu.gazebo.xacro` (ISSUE-015). `/imu` 49.5 Hz, frame `imu_link`.
- Time spent: —
- In report: yes

## ISSUE-010 — The Hiwonder bridge always publishes a static `map->odom` TF
- Date: 2026-10-12
- Component: Gazebo, SLAM
- Status: FIXED
- Command that fails: `ros2 launch robot_gazebo room_worlds.launch.py`, then `ros2 launch robot_gazebo slam.launch.py` (as in the wiki)
- Error: two sources publish `map->odom` (static TF in `ros_ign_bridge.launch.py` and `spwan_model.launch.py`, plus slam_toolbox/AMCL).
- Cause (verified by reading the code): `map_static_tf` is returned unconditionally, independent of the `nav` argument.
- Fix: `rosorin_navigation/launch/sim.launch.py` builds the bridge itself; the static TF is only enabled with `static_map_tf:=true`.
  Check: with SLAM running, `tf2_echo map odom` shows the value from slam_toolbox.
- Time spent: 0.2 h
- In report: yes

## ISSUE-009 — `ros2_control_node` crashes: the URDF has no `<ros2_control>` tag
- Date: 2026-10-12
- Component: Gazebo
- Status: WORKAROUND
- Command that fails: `room_worlds.launch.py` (which calls `spwan_model.launch.py`)
- Error:
  ```
  [gz_ros2_control]: Error parsing URDF in gz_ros2_control plugin, plugin not active : no ros2_control tag
  [ERROR] [ros2_control_node-2]: process has died [... exit code -6 ...]
  [spawner_joint_state_broadcaster]: Could not contact service /controller_manager/list_controllers
  ```
- Cause (verified): the URDF drives the robot with Ignition's `MecanumDrive` plugin and publishes `/joint_states` with
  `JointStatePublisher`; the ros2_control configuration (`robot_config.yaml`, diff_drive) is leftover and does not match the robot.
- Fix: `sim.launch.py` drops `ros2_control_node`, the spawners and `joint_state_publisher` (that node also republished
  `/joint_states` onto itself). The fixed URDF no longer loads the `ign_ros2_control` plugin, so the error line is gone.
- Time spent: 0.2 h
- In report: yes

## ISSUE-008 — All furniture is black in Gazebo (ogre2 on Mesa D3D12)
- Date: 2026-10-12
- Component: Env, Gazebo
- Status: FIXED
- Command that fails: `room_worlds.launch.py` (the GUI uses `<engine>ogre2</engine>` from the world SDF)
- Error: every textured mesh (sofa, bed, table) renders solid black. Picture: `docs/images/gazebo_ogre2_black.png`.
- Cause (verified by comparison): meshes and textures are installed; a second GUI opened with
  `ign gazebo -g --render-engine-gui ogre` on the same server shows the textures correctly. The fault is in ogre2 on Mesa D3D12.
- Fix: `sim.launch.py` adds `--render-engine-gui ogre` (argument `gui_render_engine`, default `ogre`). The server keeps ogre2 for the sensors.
- Time spent: 0.3 h
- In report: yes

## ISSUE-007 — Ignition crash `OGRE EXCEPTION ... GL3PlusTextureGpu::copyTo`
- Date: 2026-10-12
- Component: Env, Gazebo
- Status: FIXED
- Command that fails: `room_worlds.launch.py`
- Error:
  ```
  [ign gazebo-1] terminate called after throwing an instance of 'Ogre::UnimplementedException'
  [ign gazebo-1]   what():  OGRE EXCEPTION(9:UnimplementedException):  in GL3PlusTextureGpu::copyTo
  ... in ignition::gazebo::v6::systems::SensorsPrivate::RenderThread()
  ```
- Cause (verified): `glxinfo` reports `Max core profile version: 4.2` with Mesa D3D12; the render thread of the Sensors system
  (ogre2, for the gpu_lidar and the depth camera) needs a newer GL.
- Fix: `MESA_GL_VERSION_OVERRIDE=4.5` (set in `sim.launch.py`). After the fix: no crash, `/scan` has data.
- Time spent: 0.2 h
- In report: yes

## ISSUE-006 — `package 'holonomic_sim' not found` when running the launch files from the wiki
- Date: 2026-10-12
- Component: Gazebo
- Status: FIXED
- Command that fails:
  ```bash
  ros2 launch robot_gazebo worlds.launch.py
  ```
- Error:
  ```
  [ERROR] [launch]: Caught exception in launch (see debug for traceback): "package 'holonomic_sim' not found, ...
  ```
- Cause (verified): `worlds.launch.py:27` and `room_worlds.launch.py:24` call `get_package_share_directory('holonomic_sim')`, a package that is not
  in `simulations.zip`; the result is unused. In addition, xacro needs `DEPTH_CAMERA_TYPE` from `.typerc`
  (`environment variable 'DEPTH_CAMERA_TYPE' is not set`).
- Fix: new launch `ros2 launch rosorin_navigation sim.launch.py` (without the `holonomic_sim` line, `DEPTH_CAMERA_TYPE` defaults to
  `aurora`). The originals stay unchanged.
- Time spent: 0.2 h
- In report: yes

## ISSUE-005 — RViz smeared while the robot moves (default Nav2 config)
- Date: 2026-10-12
- Component: Nav2 (TurtleBot3 burger)
- Status: FIXED
- Command that fails:
  ```bash
  ros2 launch nav2_bringup rviz_launch.py
  ```
- Error: while the robot moves, a cloud of flickering green arrows surrounds it and the robot model is not visible.
- Cause (verified from window screenshots): `nav2_default_view.rviz` enables the "Amcl Particle Swarm" (hundreds of arrows redrawn
  every frame) and disables "RobotModel". `rviz_launch.py` in Humble also does not pass `use_sim_time`. The RViz frame itself stays sharp.
- Fix: use `src/rosorin_navigation/rviz/nav2_clean.rviz` (RobotModel on, particles off):
  ```bash
  rviz2 -d src/rosorin_navigation/rviz/nav2_clean.rviz --ros-args -p use_sim_time:=true
  ```
  Any remaining smear while moving is a hypothesis (WSLg compressing the image over RDP), not verified.
- Time spent: 0.3 h
- In report: yes

## ISSUE-004 — Phantom obstacles in the costmap, goal aborted
- Date: 2026-10-12
- Component: Nav2 (TurtleBot3 burger, pipeline test)
- Status: FIXED
- Command that fails: set "2D Pose Estimate" by hand in RViz, then send a "2D Goal Pose".
- Error: the costmap shows obstacles where there are no walls; Nav2 reports the goal as `ABORTED`.
- Cause (verified): the 2D Pose Estimate had the wrong heading, so AMCL initialised away from the true pose; the LiDAR scan was
  projected wrongly onto the map and marked as obstacles in the costmap.
- Fix:
  1. Read the true robot pose from Gazebo:
     ```bash
     gz model -m burger -p
     ```
  2. Publish `/initialpose` from those coordinates (replace `<x> <y>` and the quaternion `<qz> <qw>` of the yaw):
     ```bash
     ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
       "{header: {frame_id: map}, pose: {pose: {position: {x: <x>, y: <y>}, orientation: {z: <qz>, w: <qw>}}}}"
     ```
  3. Clear the old costmaps:
     ```bash
     ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap
     ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap
     ```
- Time spent: — (not recorded)
- In report: yes

## ISSUE-003 — Gazebo at 5.8 FPS, very slow simulation
- Date: 2026-10-12
- Component: Env, Gazebo
- Status: FIXED
- Command that fails: open Gazebo with TurtleBot3 `waffle`.
- Error: Gazebo shows about 5.8 FPS, a low real-time factor, and Nav2 reacts late.
- Cause (verified): WSLg rendered through D3D12 on the integrated Intel GPU instead of the NVIDIA RTX; the `waffle` model (with a
  camera) is heavier than `burger`; WSL had too little RAM.
- Fix:
  1. Force Mesa to use the NVIDIA GPU (add to `~/.bashrc`):
     ```bash
     export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
     ```
     Check: `glxinfo -B | grep -i renderer` must show NVIDIA.
  2. Change the model: `export TURTLEBOT3_MODEL=burger` (instead of `waffle`).
  3. Raise the RAM of WSL in `%UserProfile%\.wslconfig` (Windows), then `wsl --shutdown`:
     ```ini
     [wsl2]
     memory=8GB
     ```
- Result after the fix: 61 FPS, real-time factor 0.99.
- Time spent: — (not recorded)
- In report: yes

## ISSUE-002 — Nav2 reports `Invalid frame ID "odom"`: the robot does not spawn in Gazebo
- Date: 2026-10-12
- Component: Gazebo, Nav2
- Status: FIXED
- Command that fails: one combined launch starting Gazebo + Nav2 bringup + RViz together.
- Error:
  ```
  Invalid frame ID "odom" ...
  ```
- Cause (verified): the combined launch times out while spawning the robot (slow Gazebo start-up), so the robot never appears and
  there is no `/odom` and no TF `odom->base_footprint`. A stale `gzserver` from a previous run made it worse.
- Fix: clean up old processes, then use three terminals and open each one only after the previous one is ready:
  ```bash
  pkill -f gzserver; pkill -f gzclient; pkill -f rviz2
  # T1: Gazebo - wait until the robot appears in the Gazebo window
  # T2: Nav2 bringup (use_sim_time:=True, map:=...)
  # T3: RViz
  ```
  The verbatim commands of each terminal are in `COMMANDS.md`.
- Time spent: — (not recorded)
- In report: yes

## ISSUE-001 — The default WSL distro is Ubuntu 24.04, ROS 2 Humble needs 22.04
- Date: 2026-10-12
- Component: Env
- Status: FIXED
- Command that fails: `wsl --install` (the default distro is Ubuntu 24.04).
- Error: there is no `ros-humble-*` package for Ubuntu 24.04 (Noble); Humble ships binaries only for 22.04 (Jammy).
- Cause (verified): ROS 2 Humble targets Ubuntu 22.04.
- Fix: install the distro explicitly in PowerShell and work inside it:
  ```powershell
  wsl --install -d Ubuntu-22.04
  ```
- Time spent: — (not recorded)
- In report: yes
