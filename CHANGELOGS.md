# Changelog

All notable changes to this project. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Issue numbers refer to [`docs/DEBUG_LOG.md`](docs/DEBUG_LOG.md).

## [Unreleased]

### Planned
- Port Nav2 bringup (`robot_gazebo/launch/include/navigation.launch.py`) to `rosorin_navigation`.
- Multi-waypoint follower based on `nav2_simple_commander`, CSV logging to `results/nav_runs/`.
- Improve Real Time Factor of the ROSOrin simulation (ISSUE-012).

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
- Real Time Factor 0.7–0.95 in `robocup_home` (ISSUE-012).
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
