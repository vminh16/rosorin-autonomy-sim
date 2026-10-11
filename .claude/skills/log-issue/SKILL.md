---
name: log-issue
description: Ghi một lỗi mới (hoặc cập nhật lời giải) vào docs/DEBUG_LOG.md theo đúng mẫu. Dùng ngay khi một lệnh build/run/train/eval thất bại, trước khi bắt đầu sửa.
argument-hint: "[mô tả ngắn lỗi] hoặc [ISSUE-NNN fixed: cách sửa]"
---

Mục tiêu: DEBUG_LOG là nguồn cho mục "Problems & Solutions" của báo cáo, nên mỗi mục phải cụ thể và tái hiện được.

Đầu vào: $ARGUMENTS

1. Đọc `docs/DEBUG_LOG.md` (tính từ gốc repo), tìm số ISSUE lớn nhất hiện có.
2. Nếu đầu vào bắt đầu bằng `ISSUE-NNN`: cập nhật mục đó (Trạng thái, Nguyên nhân, Cách sửa, Thời gian mất). Dừng.
3. Nếu là lỗi mới: tạo `ISSUE-<số tiếp theo>` ở đầu danh sách (dưới khối comment mẫu), điền:
   - Ngày hôm nay
   - Thành phần, suy ra từ việc đang làm: `Env/WSL` | `Gazebo` | `SLAM` | `Nav2` | `rosorin_navigation` | `Build/CI`
   - Trạng thái `OPEN`
   - Lệnh gây lỗi: lấy nguyên văn lệnh vừa chạy trong phiên này
   - Lỗi: chỉ 1–5 dòng quan trọng nhất của log, không dán cả traceback
   - Nguyên nhân: ghi "giả thuyết:" nếu chưa xác minh
4. Không sửa lỗi trong bước này. Báo lại số ISSUE vừa tạo.
