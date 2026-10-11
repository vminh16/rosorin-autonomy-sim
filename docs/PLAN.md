# Plan

Deadline: `<YYYY-MM-DD>`. Phạm vi repo này: Part 1. Nếu thiếu thời gian, cắt theo mục "Cắt giảm" bên dưới, không cắt P0.

## Mức ưu tiên
- **P0** — bắt buộc để đạt yêu cầu đề bài. Làm trước tiên.
- **P1** — làm bài nổi bật (log số liệu waypoint, so sánh SLAM, video chỉn chu).
- **P2** — chỉ làm khi P0 + P1 đã xong.

## Timebox (dừng lại khi vượt, ghi DEBUG_LOG, chuyển phương án dự phòng)
| Việc | Timebox | Phương án dự phòng khi vượt |
|---|---|---|
| Cài ROS 2 + sim Hiwonder chạy được | 1 ngày | Dùng ảnh máy ảo/Docker Hiwonder cung cấp (nếu có) |
| SLAM ra bản đồ dùng được | 0.5 ngày | Đổi thuật toán SLAM được wiki hỗ trợ; giảm tốc độ lái |
| Nav2 chạy trên bản đồ | 1 ngày | Dùng nguyên file param mẫu của Hiwonder, chỉ đổi đường dẫn map |

## Việc cần làm (P0)
- [x] Cài Ubuntu 22.04 (WSL2) + ROS 2 Humble, Nav2, slam_toolbox, cartographer, Gazebo (`docs/ENVIRONMENT.md`)
- [x] Kiểm tra pipeline Gazebo + Nav2 bằng TurtleBot3 burger (ISSUE-001..004)
- [x] Import code Hiwonder vào `src/simulations/` (commit nguyên bản trước)
- [x] Sửa launch Hiwonder (bản copy trong `rosorin_navigation`) để chạy được trên WSL2 (ISSUE-006..010)
- [x] Gazebo + RViz LiDAR → chụp ảnh màn hình (`docs/images/`)
- [ ] Teleop bằng bàn phím với ROSOrin (đã lái bằng `/cmd_vel`, chưa thử teleop tương tác)
- [ ] SLAM → lưu map vào `maps/` (SLAM đã chạy, chưa vẽ hết nhà và lưu map)
- [ ] Port Nav2 (`navigation.launch.py` của Hiwonder) sang `rosorin_navigation`
- [ ] Nav2 single goal
- [ ] Script multi-waypoint (`src/rosorin_navigation/`) dựa trên mẫu `nav2_simple_commander`
- [ ] Quay video thô từng bước (dựng sau)

## P1
- [ ] Log CSV cho mỗi lần chạy waypoint (`results/nav_runs/`), tổng hợp tỷ lệ tới đích + thời gian
- [ ] So sánh slam_toolbox và cartographer trên cùng world (chất lượng map, thời gian)

## Hoàn thiện + tái hiện
- [ ] Dựng video Part 1 (3–5 phút)
- [ ] Hoàn thiện README + `COMMANDS.md`
- [ ] Clone sạch ở thư mục khác, làm theo README → sửa chỗ hỏng (F.6)
- [ ] Chạy `/status` lần cuối, tick hết DELIVERABLES

## Cắt giảm khi thiếu thời gian (cắt từ dưới lên)
1. So sánh slam_toolbox vs cartographer (P1)
2. Tổng hợp số liệu CSV → giữ log thô, bỏ phân tích
Không bao giờ cắt: SLAM + map, single goal, multi-waypoint, video Part 1, README.
