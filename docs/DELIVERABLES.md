# Deliverables Checklist

Đối chiếu 1–1 với đề bài. Chỉ tick khi có bằng chứng (đường dẫn file/link) ở cột cuối.
Phạm vi repo này: Part 1. Part 2 (world models) theo dõi ở repo riêng.

## Part 1 — ROSOrin Pro Simulation
Tài liệu chính thức: https://wiki.hiwonder.com/projects/rosorin-pro/en/latest/

| # | Yêu cầu | Ưu tiên | Xong | Bằng chứng |
|---|---|---|---|---|
| 1.1 | Cài đặt Gazebo simulation của ROSOrin Pro | P0 | [ ] | `docs/ENVIRONMENT.md` |
| 1.2 | Chạy và điều khiển robot (teleop / cmd_vel) | P0 | [ ] | |
| 1.3 | Hiển thị cảm biến mô phỏng (LiDAR trong RViz) | P0 | [ ] | |
| 1.4 | Chạy SLAM và tạo bản đồ | P0 | [ ] | |
| 1.5 | Lưu bản đồ (.pgm + .yaml) | P0 | [ ] | `maps/` |
| 1.6 | Điều hướng tự động trên bản đồ đã lưu | P0 | [ ] | |
| 1.7 | Single-goal navigation | P0 | [ ] | |
| 1.8 | Multi-point (waypoint) navigation | P0 | [ ] | `src/rosorin_navigation/`, `results/nav_runs/` |
| 1.9 | Video demo 3–5 phút | P0 | [ ] | `docs/VIDEOS.md` |
| 1.10 | Source code, config, commands, README | P0 | [ ] | `COMMANDS.md`, `README.md` |
| 1.11 | Báo cáo ngắn: setup, kết quả, lỗi, cách sửa | P0 | [ ] | `docs/DEBUG_LOG.md` → báo cáo |

## Final submission (phần thuộc Part 1)

| # | Yêu cầu | Xong | Bằng chứng |
|---|---|---|---|
| F.1 | GitHub repo / source code | [ ] | URL |
| F.2 | README với hướng dẫn tái hiện | [ ] | `README.md` |
| F.3 | Video demo Part 1 | [ ] | `docs/VIDEOS.md` |
| F.6 | Kiểm tra tái hiện: clone sạch + làm theo README chạy được | [ ] | ghi ngày test |

## Tiêu chí chấm (từ đề) — dùng để tự đánh giá trước khi nộp
Technical understanding · Implementation · Experimental results · Debugging ability · Analysis · Reproducibility.
Không chấm theo lượng tài nguyên tính toán.
