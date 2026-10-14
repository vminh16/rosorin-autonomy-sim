# Demo video recording

Scripts that recorded the demo video ([release v1.0.0](https://github.com/vminh16/rosorin-autonomy-sim/releases/tag/v1.0.0)).
They run the same commands as the README and show them typed in a console window, so every step of the video can be
replayed from this repository.

| File | Role |
|---|---|
| `record_take1.sh` | steps 1-5: simulation, driving, LiDAR, SLAM with autonomous exploration, map saving |
| `record_take2.sh` | steps 6-7: single goal and 7-waypoint mission on the saved map (simulation restarted) |
| `post.py` | cuts the recordings, speeds up the long parts (marked ×2 / ×3 in the video), burns in the subtitles |
| `drive.py` | step 2: publishes `/cmd_vel` (the topic `teleop_twist_keyboard` uses) for forward, sideways and a turn |
| `demo_world.sdf` | `worlds/robocup_home.sdf` without the side panels, for a clear top view |
| `demo_gui.config`, `demo_*.rviz` | window layout of Gazebo and RViz for 1920x1080 |
| `backdrop.py`, `term_view.py` | background window and the console shown in the video |

```bash
sudo apt install -y ffmpeg python3-pil python3-tk
DEMO_DIR=/tmp/rosorin_demo tools/demo/record_take1.sh    # about 6 min; writes raw.mkv, events.txt, maps/demo_house.*
DEMO_DIR=/tmp/rosorin_demo tools/demo/record_take2.sh    # about 3 min; raw2.mkv, events2.txt
python3 tools/demo/post.py /tmp/rosorin_demo             # rosorin_demo_en.mp4
```

Needs an X11 session with a 1920x1080 screen and an NVIDIA GPU (`h264_nvenc`; use `-c:v libx264` in the scripts
otherwise). Every process a script starts is stopped at its end.
