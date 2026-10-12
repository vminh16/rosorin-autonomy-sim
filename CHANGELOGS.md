# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Issue numbers refer to [`docs/DEBUG_LOG.md`](docs/DEBUG_LOG.md).

## [Unreleased]

## 2026-10-12 — Re-check against the real documentation, navigation

| Task | Bug | Result | Commit |
|---|---|---|---|
| Compare the simulated robot with the Hiwonder wiki and fix the differences | Drive plugin used wheel radius 0.05 (real 0.04): robot 0.8x slower than commanded, no sideways motion. LiDAR 156 deg (real 360 deg), no IMU, mass 40 kg | Fidelity tests 10/10 green; achieved/commanded velocity 1.00 forward, sideways and turning | `4d85581` |
| Saved SLAM map of the house | First scan ruined by the flip (ISSUE-016) | `maps/house`: 99.7% of walls detected, no offset | `0169f4a` |
| Wheel speed limited to the real motor (ISSUE-017) | Robot reached 1.0 m/s and 5 rad/s; real motors allow 0.461 m/s | `probe_physics.py` 7/7 PASS, top speed 0.461 m/s / 2.643 rad/s | `6916228` |
| Traction-limited drive plugin (ISSUE-016) | Velocity-override drive climbed furniture, flipped and flew off; `/odom` had two publishers | Collision probe 9/9 PASS (was 5/9), velocity 1.00, one `/odom` publisher, 23 package tests green | `79aeecc` |
| Nav2 on `maps/house` (`navigation.launch.py`, fixed vendor params), MPPI controller (ISSUE-018) | Vendor DWB stalled on a U-shaped path (5/6 goals); robot_radius 0.07 (real 0.177); smoother capped at 0.26 m/s | 6/6 goals, final error 0.11 m mean (true pose) | — |
| Multi-waypoint follower with CSV log | — | 2 laps, 14/14 waypoints, 16.0 s per waypoint | — |
| 14-waypoint route through every room (`waypoints_extended.yaml`), GUI simulation | — | 14/14, 56.6 m in 216 s, final error 0.12 m mean (true pose) | — |

## [0.3.0] — 2026-10-12 — Smooth rendering and real-time simulation

### Changed
- Furniture in `robocup_home` is spawned by `sim.launch.py` as **static** models (same positions as upstream
  `spawn_objects.launch.py`). Real Time Factor 0.50 → 1.00 (ISSUE-012).
- `robocup_home` now loads `rosorin_navigation/worlds/robocup_home.sdf`: physics step 30 ms → 10 ms,
  so the robot pose updates 100×/s instead of 33×/s. `/odom` 20 → 50 Hz, `/scan` 5 → 10 Hz.
- RViz configs (`slam.rviz` copy, `nav2_clean.rviz`) render at 60 fps instead of 30 (measured 57 fps).
- `slam.launch.py` uses `rosorin_navigation/rviz/slam.rviz`.

### Added
- `sim.launch.py` arguments: `furniture`, `camera`, `gui`, `world_file`, `robot_xacro`.

## [0.2.0] — 2026-10-12 — ROSOrin Pro simulation

### Added
- Hiwonder ROSOrin Pro simulation packages `robot_gazebo` and `rosorin_description` in `src/simulations/`,
  imported unmodified from the Hiwonder wiki (`simulations.zip`, V1.0.0 2025-05-29), plus `.typerc`.
- `rosorin_navigation/launch/sim.launch.py`: Ignition Gazebo + ROSOrin + ROS bridge.
  Arguments: `world` (`robocup_home` | `empty`), `gui_render_engine`, `static_map_tf`, `x`, `y`, `yaw`.
- `rosorin_navigation/launch/slam.launch.py`: slam_toolbox (sync, upstream `slam.yaml`) + RViz with sim time.
- Environment: `ros-humble-ros-ign-gazebo`, `ros-humble-ros-ign-bridge`, `ros-humble-ign-ros2-control`,
  `ros-humble-ros2-control`, `ros-humble-ros2-controllers`.
- `COMMANDS.md` with verified commands; screenshots in `docs/images/`.

### Fixed (in copies; upstream files untouched)
- Launch crash `package 'holonomic_sim' not found` and missing `DEPTH_CAMERA_TYPE` (ISSUE-006).
- Ignition abort `OGRE EXCEPTION ... GL3PlusTextureGpu::copyTo` on WSL2 via `MESA_GL_VERSION_OVERRIDE=4.5` (ISSUE-007).
- Textured meshes rendered black: GUI now uses the ogre (v1) engine (ISSUE-008).
- Removed `ros2_control_node` / spawner / `joint_state_publisher` that crashed or looped on `/joint_states` (ISSUE-009).
- Static `map→odom` TF is now opt-in so it no longer conflicts with SLAM/AMCL (ISSUE-010).
- `/cmd_vel` is bridged to the robot's `/controller/cmd_vel`, so standard teleop and Nav2 work without remapping.

### Known issues
- IMU publishes no data: upstream URDF never includes the IMU sensor (ISSUE-011).
- Real Time Factor 0.7–0.95 in `robocup_home` (ISSUE-012) — fixed in 0.3.0.
- Teleop by keyboard, map saving and Nav2 on ROSOrin not yet verified.

## [0.1.0] — 2026-10-12 — Workspace and environment

### Added
- ROS 2 Humble colcon workspace from `athackst/vscode_ros2_workspace`; devcontainer distro set to `humble`.
- `rosorin_navigation` package skeleton (ament_python).
- `rosorin_navigation/rviz/nav2_clean.rviz`: Nav2 view with robot model on and AMCL particle cloud off (ISSUE-005).
- Docs: `README.md`, `CLAUDE.md`, `docs/ENVIRONMENT.md`, `docs/DEBUG_LOG.md`, `docs/PLAN.md`, `docs/DELIVERABLES.md`,
  `docs/agents/` (issue tracker, triage labels, domain docs).
- Claude Code skills `/log-issue` and `/status`.

### Fixed
- Environment issues found while validating Nav2 with TurtleBot3 (ISSUE-001..004): Ubuntu 22.04 distro on WSL,
  robot not spawning with the combined launch, low Gazebo FPS on the integrated GPU, phantom costmap obstacles.
- `.gitignore`: broken `site/*` line, stale `part1_rosorin/` and `part2_world_models/` paths.
