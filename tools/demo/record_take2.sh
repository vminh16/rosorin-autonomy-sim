#!/bin/bash
# Record the ROSOrin demo: runs the real commands, mirrors key output to the demo console,
# logs scene events (seconds from the start of the recording) to events.txt.
# Every process it starts is tracked by PID and stopped at the end.
set -u
S=$(cd "$(dirname "$0")" && pwd)                          # this folder: scripts, world, GUI and RViz configs
R=$(cd "$S/../.." && pwd)                                 # repository root
D=${DEMO_DIR:-/tmp/rosorin_demo}                          # recordings, logs, saved map
mkdir -p $D
LOG=$D/term.log; EV=$D/events2.txt; PIDS=$D/pids2.txt
cd $R
set +u; source /opt/ros/humble/setup.bash; source install/setup.bash; set -u
export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia
rm -f $D/stop $EV $PIDS $D/raw2.mkv; mkdir -p $D/runs2 $D/logs
sed -n "/# 5. Save the map/,/map: /p" $D/term_part1.log > $LOG

T0=0
now() { python3 -c "import time; print(f'{time.time()-$T0:.2f}')"; }
ev() { echo "$(now) $1" >> $EV; }
track() { echo "$1 $2" >> $PIDS; }                       # pid name
out() { printf '%b\n' "$1" >> $LOG; }
note() { out "\033[38;5;245m# $1\033[0m"; }
typecmd() {                                                 # show a command, typed
  printf '\033[1;32m$\033[0m ' >> $LOG
  local s="$1" i
  for ((i = 0; i < ${#s}; i++)); do printf '%s' "${s:$i:1}" >> $LOG; sleep 0.018; done
  printf '\n' >> $LOG; sleep 0.4
}
mirror() {                                                  # copy matching lines of a log
  tail -n 0 -F --pid=$$ "$1" 2>/dev/null | grep --line-buffered -E "$2" | \
    sed -u -E 's/^\[[a-z_]+-?[0-9]*\] //; s/\[INFO\] \[[0-9.]+\] \[[a-z_]+\]: //' >> $LOG &
  track $! "mirror"
}
cam() {                                                     # move the Gazebo GUI camera
  ign service -s /gui/move_to/pose --reqtype ignition.msgs.GUICamera --reptype ignition.msgs.Boolean \
    --timeout 3000 --req "pose: {position: {x: $1, y: $2, z: $3}, orientation: {$4}}" > /dev/null 2>&1
}
wait_for() { local i; for ((i = 0; i < $2; i++)); do eval "$1" > /dev/null 2>&1 && return 0; sleep 1; done; return 1; }
stop_pid() { kill -INT $1 2>/dev/null; }

# ---- windows and recording
python3 $S/backdrop.py $D/stop & track $! backdrop
sleep 1.5
gnome-terminal --geometry=200x15+0+745 --title="demo console" -- python3 $S/term_view.py $LOG
sleep 2
# ---- simulation (shown in take 1), started before the recording
timeout -s INT 1500 ros2 launch rosorin_navigation sim.launch.py gui:=false world_file:=$S/demo_world.sdf \
  > $D/logs/sim2.log 2>&1 & SIM=$!; track $SIM sim
sleep 4
timeout -s INT 1500 ign gazebo -g --gui-config $S/demo_gui.config --render-engine-gui ogre2 \
  > $D/logs/gui2.log 2>&1 & GUI=$!; track $GUI gui
wait_for "timeout 3 ros2 topic echo --once /odom" 90
sleep 3
cam 0.0 -7.0 8.5 "x: -0.3063 y: 0.3063 z: 0.6373 w: 0.6373"
sleep 2
ffmpeg -hide_banner -loglevel error -f x11grab -framerate 30 -video_size 1834x1016 -i :1+0,64 \
  -c:v h264_nvenc -preset p5 -cq 21 -pix_fmt yuv420p $D/raw2.mkv < /dev/null > $D/logs/ffmpeg2.log 2>&1 &
FF=$!; track $FF ffmpeg
T0=$(python3 -c "import time; print(time.time())")
ev rec_start
sleep 2

# ---- 6. Nav2 on the saved map, single goal
ev s6_nav
note "6. Navigation on the saved map: AMCL + NavFn + MPPI. SLAM stopped"
note "(take 2: simulation restarted with the robot at the start pose; same saved map)"
sleep 2
typecmd "ros2 launch rosorin_navigation navigation.launch.py map:=maps/demo_house.yaml rviz:=false"
timeout -s INT 1500 ros2 launch rosorin_navigation navigation.launch.py map:=$D/maps/demo_house.yaml \
  rviz:=false > $D/logs/nav.log 2>&1 & NAV2=$!; track $NAV2 nav
timeout -s INT 1500 rviz2 -d $S/demo_nav.rviz --ros-args -p use_sim_time:=true > $D/logs/rviz3.log 2>&1 &
RV3=$!; track $RV3 rviz_nav
wait_for "ros2 lifecycle get /bt_navigator 2>/dev/null | grep -q active" 90
sleep 3
note "goal in the bedroom: the path makes a U-turn around a wall (the goal the vendor's DWB failed)"
typecmd "ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \"{pose: {header: {frame_id: map}, pose: {position: {x: 3.0, y: -1.5}, orientation: {z: 1.0, w: 0.0}}}}\""
ev s6_goal
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 3.0, y: -1.5}, orientation: {z: 1.0, w: 0.0}}}}" \
  2>&1 | grep --line-buffered -E "accepted|finished|status" >> $LOG
ev s6_end
sleep 2

# ---- 7. waypoints
ev s7_wp
note "7. Multi-waypoint mission: config/waypoints.yaml, 7 waypoints, CSV log per run"
typecmd "ros2 run rosorin_navigation waypoint_follower --ros-args -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml"
mirror $D/logs/wp2.log "Waypoint [0-9]+/[0-9]+|Route"
timeout -s INT 400 ros2 run rosorin_navigation waypoint_follower --ros-args -p use_sim_time:=true \
  -p waypoints_file:=src/rosorin_navigation/config/waypoints.yaml -p output_dir:=$D/runs2 \
  -p timeout:=380.0 > $D/logs/wp2.log 2>&1
sleep 4
ev s7_end
sleep 2
ev rec_end

# ---- stop everything this script started
kill -INT $FF; sleep 3
echo "__END__" >> $LOG
touch $D/stop
for p in $RV3 $NAV2 $GUI $SIM; do stop_pid $p; done
sleep 8
while read -r pid name; do
  if kill -0 $pid 2>/dev/null; then echo "still running: $pid $name"; kill $pid 2>/dev/null; fi
done < $PIDS
echo "director done"
