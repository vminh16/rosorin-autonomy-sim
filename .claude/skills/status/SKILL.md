---
name: status
description: Báo cáo tiến độ so với docs/DELIVERABLES.md và docs/PLAN.md, chỉ ra việc P0 còn thiếu và rủi ro trễ hạn. Dùng đầu mỗi phiên làm việc hoặc khi hỏi "còn thiếu gì".
---

Phạm vi: chỉ Part 1 (repo này). Đường dẫn tính từ gốc repo.

1. Đọc `docs/DELIVERABLES.md`, `docs/PLAN.md`, `docs/DEBUG_LOG.md`.
2. Với mỗi ô đã tick trong DELIVERABLES: kiểm tra đường dẫn ở cột "Bằng chứng" có tồn tại thật
   (ví dụ `maps/*.yaml`, `src/rosorin_navigation/`, `results/nav_runs/*.csv`, `COMMANDS.md`). Ô tick mà thiếu bằng chứng → báo.
3. Kiểm tra bảng "Lệnh chính" trong `CLAUDE.md`: lệnh nào đã tick mà chưa có trong `COMMANDS.md` → báo.
4. Tính số ngày còn lại tới deadline (dòng `Deadline:` đầu `docs/PLAN.md`). Nếu deadline chưa điền → nhắc điền.
5. Trả lời ngắn theo đúng 4 mục:
   - **Xong**: số mục P0 / tổng P0, P1 / tổng P1
   - **P0 còn thiếu**: danh sách, mỗi mục kèm việc cụ thể tiếp theo
   - **Lỗi đang OPEN** trong DEBUG_LOG
   - **Rủi ro trễ hạn**: nếu số việc P0 còn lại không vừa thời gian, đề xuất cắt theo mục "Cắt giảm" của PLAN
6. Không sửa file nào trong skill này.
