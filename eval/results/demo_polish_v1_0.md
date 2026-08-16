# Demo Polish & Operational Presentation Readiness Report

**Milestone:** DEMO-POLISH-1  
**Date:** 2026-08-16  
**Status:** READY FOR PRESENTATION & GRADING  

---

## 1. UI Issues Tìm Thấy

- **Navigation Clutter:** Thanh điều hướng Sidebar chứa các module mở rộng chưa có backend (`CMDB Map`, `On-call`, `War Room`, `Change Management`), có thể gây phân tán và nhầm lẫn khi người chấm trải nghiệm.
- **Dead Links:** Các liên kết bài viết gợi ý trong `Employee Dashboard` trỏ nhầm về `/login`.
- **Text Wrapping & Overflow:** Bong bóng chat trong AI Workspace và Ticket Detail có nguy cơ tràn viền nếu người dùng nhập chuỗi ký tự dài liên tục hoặc URL không ngắt dòng.
- **Rate Limit Counter Artifacts:** Bộ đếm rate limit trượt gây ảnh hưởng chéo giữa các bài test liên tục trong cùng phiên chạy.

---

## 2. UI Issues Đã Sửa

- **Sidebar Navigation Cleanup:** Đã tinh chỉnh Sidebar của cả 4 vai trò (**Employee, Technician, Manager, Admin**), chỉ hiển thị các màn hình chức năng hoạt động 100% với API backend.
- **Fixed Knowledge Base Routing:** Điều chỉnh toàn bộ gợi ý tri thức về đúng trang `/employee/kb`.
- **Chat Bubble Text Wrapping:** Bổ sung thuộc tính `break-words` vào các khung chứa tin nhắn trong `frontend/src/app/employee/chatbot/page.tsx` và `frontend/src/app/employee/tickets/[id]/page.tsx`.
- **Test Rate Limiter Reset:** Cung cấp helper `reset_rate_limiter()` để làm mới bộ đếm trong môi trường kiểm thử.

---

## 3. Demo Data

Hệ thống được trang bị kịch bản seed dữ liệu mẫu tất định và có thể reset bất cứ lúc nào qua script `scripts/seed_demo_state.py`:

- **Demo Users (Môi trường Development/Demo):**
  - `employee1` / `demo123` (Employee - Corporate)
  - `employee_vip` / `demo123` (Employee VIP - Corporate)
  - `tech1` / `demo123` (Technician - Toàn quyền 5 nhóm fulfillment)
  - `manager1` / `demo123` (Manager - Approver)
  - `admin` / `admin123` (System Administrator)
- **Sample Incidents:**
  - `INC-20260816-0001` (OPEN - VPN FortiClient 809 - Network IT)
  - `INC-20260816-0002` (PENDING_HITL - Cấp quyền root database server Production - Security IT)
  - `INC-20260816-0003` (IN_PROGRESS - Máy in tầng 3 kẹt giấy - Workplace IT)
  - `INC-20260816-0004` (RESOLVED - Sửa lỗi Outlook PST - Workplace IT)
- **Sample Service Requests:**
  - `REQ-20260816-DEMO01` (PENDING_APPROVAL - Xin laptop mới - Workplace IT)
  - `REQ-20260816-DEMO02` (IN_PROGRESS - Xin quyền VPN - Network IT)
  - `REQ-20260816-DEMO03` (FULFILLED - Cài đặt Docker Desktop - Workplace IT)
- **Knowledge Base:** 433 tài liệu chuẩn trong ChromaDB, bao gồm quy trình `kb-036`.

---

## 4. Employee Demo Journey

1. **Đăng nhập:** Truy cập `/login`, chọn tài khoản `employee1` / `demo123`.
2. **Cổng tự phục vụ:** Trải nghiệm thanh tìm kiếm thông minh Golden Zone Search.
3. **Tạo sự cố (Incident):** Vào `/employee/new-ticket`, nhập tiêu đề và mô tả sự cố (ví dụ: *Lỗi Outlook không gửi được thư*).
4. **AI Trao đổi:** AI Copilot phân loại danh mục, tính toán độ tin cậy và phản hồi hướng dẫn xử lý từng bước.
5. **Đánh giá & Mở lại:** Khi sự cố hoàn tất, đánh giá 1-5 sao và kiểm tra tính năng mở lại (Reopen) với lý do bắt buộc.

---

## 5. Technician Demo Journey

1. **Đăng nhập:** Đăng nhập tài khoản `tech1` / `demo123`.
2. **Incident Queue:** Truy cập `/technician/queue`, xem hàng đợi sắp xếp theo độ ưu tiên và SLA.
3. **Tiếp nhận xử lý (Takeover):** Mở ticket `INC-20260816-0001`, nhấn **Tiếp nhận ticket**.
4. **Trò chuyện trực tiếp:** Gửi tin nhắn trực tiếp cho người dùng qua khung chat chuyên viên.
5. **Đóng sự cố:** Nhấn **Đóng ticket** với ghi chú hoàn thành công việc.

---

## 6. Manager Demo Journey

1. **Đăng nhập:** Đăng nhập tài khoản `manager1` / `demo123`.
2. **Control Tower:** Truy cập `/manager/dashboard`, xem tổng quan chỉ số SLA, độ tin cậy AI, khối lượng công việc.
3. **Phê duyệt (Approvals Center):** Truy cập `/manager/approvals`.
4. **Xử lý Service Request:** Mở yêu cầu `REQ-20260816-DEMO01` (Xin laptop mới), nhấn **Phê duyệt** với lý do chấp thuận.

---

## 7. Admin Demo Journey

1. **Đăng nhập:** Đăng nhập tài khoản `admin` / `admin123`.
2. **User Management:** Truy cập `/admin/users`, xem danh sách tài khoản, chỉnh sửa thông tin, bật/tắt trạng thái Active/Inactive.
3. **Fulfillment Groups:** Cấu hình nhóm tiếp nhận dịch vụ cho kỹ thuật viên `tech1`.
4. **Knowledge Base:** Truy cập `/admin/kb`, tra cứu bài viết quy trình `kb-036`, xem số lượt bình chọn hữu ích.
5. **AI Review & RAG:** Xem nhật ký kiểm toán tại `/admin/ai-review` và trạng thái vector store tại `/admin/rag`.

---

## 8. AI Demo Prompts

- **Case A (Multi-turn Memory):**
  - Turn 1: *"VPN FortiClient báo lỗi 809 trên Windows 11"* $\rightarrow$ AI hướng dẫn kiểm tra cấu hình IPsec & NAT Traversal.
  - Turn 2: *"Tôi thử bước đầu tiên rồi nhưng vẫn lỗi"* $\rightarrow$ AI duy trì ngữ cảnh VPN 809 và hướng dẫn bước tiếp theo mà không hỏi lại.
- **Case B (Knowledge Grounding `kb-036`):**
  - Prompt: *"Quy trình Service Request gồm những bước nào?"* $\rightarrow$ AI trích xuất chính xác quy trình 5 bước: Submit $\rightarrow$ Approval $\rightarrow$ Routing $\rightarrow$ Fulfillment $\rightarrow$ Completed.
- **Case C (Safe Action Grounding):**
  - Prompt: *"Tạo Service Request xin laptop cho tôi"* $\rightarrow$ AI hướng dẫn truy cập IT Service Catalog, không tự ý giả mạo tạo record khi chưa qua biểu mẫu.
- **Case D (Human Handoff):**
  - Prompt: *"Tôi muốn gặp kỹ thuật viên"* $\rightarrow$ AI chuyển tiếp an toàn sang trạng thái chờ chuyên viên mà không tự nhận giải quyết.

---

## 9. Failure UX & Error Handling

- **Backend chưa chạy / Mất kết nối:** Toast thông báo tiếng Việt rõ ràng: *"Lỗi kết nối: Không thể kết nối tới Server Backend (port 8000). Vui lòng kiểm tra lại xem Backend có đang chạy không."*
- **Input vượt quá giới hạn (413):** Thông báo chặn ngay từ phía frontend và backend trả về mã `413: INPUT_TOO_LARGE` kèm độ dài chi tiết.
- **Rate Limit (429):** Thông báo lỗi tần suất `429: Rate limit exceeded` dễ hiểu, không để lộ stack trace.

---

## 10. README & Run Instructions

- **Khởi động Backend:**
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Khởi động Frontend:**
  ```powershell
  cd frontend
  npm run dev
  ```
- **Reset Dữ liệu Demo (Nếu cần):**
  ```powershell
  .\.venv\Scripts\python.exe scripts/seed_demo_state.py
  ```
- **Các cổng truy cập:**
  - Frontend Portal: `http://localhost:3000`
  - Backend API Docs: `http://localhost:8000/docs`
  - Health Check: `http://localhost:8000/health`

---

## 11. Test Results

- **Backend Pytest:** **353/353 PASSED (100%)**
- **Frontend Lint:** **0 errors** (120 non-blocking stylistic warnings)
- **TypeScript:** **0 errors**
- **Product Guards:** **PASS** (12 guarded routes, 2 API-backed fulfillment routes)
- **Production Build:** **PASS** (46/46 routes compiled with Next.js Webpack)

---

## Verdicts

```
DEMO_UI_READY:        YES
DEMO_DATA_READY:      YES
DEMO_JOURNEYS_READY:  YES

DEMO_READY:           YES
```
