# D3 — HITL Approval Data Flow (Luồng Phê Duyệt Có Con Người Tham Gia)

> **Tài liệu bổ sung:** Sơ đồ này làm rõ một phần của kiến trúc MVP P-236. Nội dung có thể được điều chỉnh trong quá trình tiếp tục tích hợp và không đại diện cho kiến trúc production cuối cùng.
>
> `Core MVP` biểu thị thành phần thuộc phạm vi MVP, không mặc định rằng thành phần đã hoàn thiện hoặc được xác minh end-to-end.

---

## 1. Sơ Đồ D3: Human-in-the-Loop (HITL) Approval Flow

Sơ đồ thể hiện quy trình xử lý khi tác nhân AI phát hiện tác vụ có rủi ro cao hoặc cần phê duyệt nghiệp vụ từ **Technician**, **Manager** hoặc **Admin**.

```mermaid
sequenceDiagram
    participant Agent as 🕸️ LangGraph Agent
    participant DB as 🗄️ SQLite Database
    participant API as 🚀 FastAPI Backend (/api/v1/tickets)
    participant UI as 🌐 Web Frontend (Portal / HITL Dashboard)
    actor Reviewer as 👨‍💻 Technician / Manager / Admin
    actor User as 👤 Employee

    Agent->>DB: 1. Đánh dấu Ticket Status: PENDING_HITL (Lưu hitl_reason & risk_score)

    Reviewer->>UI: 2. Truy cập bảng điều khiển hàng đợi phê duyệt
    UI->>API: 3. GET /api/v1/tickets/pending-hitl (Bearer JWT)
    API->>API: 4. Kiểm tra quyền hạn (Role: Technician / Manager / Admin)
    API->>DB: 5. Lấy danh sách tác vụ chờ duyệt
    DB-->>API: 6. Danh sách các vé PENDING_HITL
    API-->>UI: 7. Hiển thị thông tin sự cố & Giải pháp AI đề xuất

    alt Quyết định Phê Duyệt (Approve)
        Reviewer->>UI: 8a. Nhấn "Phê duyệt" (Ghi nhận ý kiến)
        UI->>API: 9a. POST /api/v1/tickets/{id}/hitl-decision (action: "approve")
        API->>DB: 10a. Cập nhật Status: RESOLVED
        API->>DB: 11a. Ghi nhận nhật ký kiểm toán (audit_logs)
        API-->>UI: 12a. Thông báo phê duyệt thành công
    else Quyết định Chỉnh Sửa & Phê Duyệt (Edit & Approve)
        Reviewer->>UI: 8b. Sửa đổi nội dung giải pháp & Nhấn "Lưu & Duyệt"
        UI->>API: 9b. POST /api/v1/tickets/{id}/hitl-decision (action: "edit_approve", solution)
        API->>DB: 10b. Cập nhật Status: RESOLVED (với giải pháp đã sửa)
        API->>DB: 11b. Ghi nhận nhật ký kiểm toán & sự can thiệp
    else Quyết định Từ Chối Đề Xuất (Reject Proposal)
        Reviewer->>UI: 8c. Nhấn "Từ chối đề xuất AI" (Nhập lý do)
        UI->>API: 9c. POST /api/v1/tickets/{id}/hitl-decision (action: "reject", reason)
        API->>DB: 10c. Cập nhật Status: IN_PROGRESS & Đưa vào hàng đợi phân công
        API->>DB: 11c. Ghi nhận nhật ký kiểm toán hành động từ chối
    end

    User->>UI: 13. Mở xem chi tiết ticket trên Portal
    UI->>API: 14. GET /api/v1/tickets/{id}
    API->>DB: 15. Lấy trạng thái ticket
    DB-->>API: 16. Trạng thái (RESOLVED hoặc IN_PROGRESS)
    API-->>UI: 17. Trạng thái và kết quả xử lý
    UI-->>User: 18. Hiển thị kết quả xử lý sự cố
```

---

## 2. Quy Tắc Xử Lý Khi Từ Chối Đề Xuất (Reject Behavior)

Khi Kỹ thuật viên, Quản lý hoặc Quản trị viên từ chối đề xuất tự động của AI:
1. **Không đóng vé:** Hệ thống không chuyển vé sang trạng thái `CLOSED` trong luồng Reject của MVP để tránh bỏ sót sự cố của nhân viên.
2. **Chuyển sang xử lý thủ công:** Trạng thái vé được chuyển thành `IN_PROGRESS` và đưa vào hàng đợi phân công cho Kỹ thuật viên chuyên trách xử lý trực tiếp.
3. **Lưu vết đầy đủ (*Audit Trail*):** Mọi thao tác Phê duyệt, Chỉnh sửa hay Từ chối đều được ghi nhận chi tiết vào bảng `audit_logs` nhằm hỗ trợ truy vết và kiểm toán hệ thống.
