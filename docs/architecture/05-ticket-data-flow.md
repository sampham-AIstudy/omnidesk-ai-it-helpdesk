# D1 — Ticket Data Flow (Luồng Dữ Liệu Xử Lý Sự Cố)

> **Tài liệu bổ sung:** Sơ đồ này làm rõ một phần của kiến trúc MVP P-236. Nội dung có thể được điều chỉnh trong quá trình tiếp tục tích hợp và không đại diện cho kiến trúc production cuối cùng.
>
> `Core MVP` biểu thị thành phần thuộc phạm vi MVP, không mặc định rằng thành phần đã hoàn thiện hoặc được xác minh end-to-end.

---

## 1. Giai Đoạn 1: Tiếp Nhận Vé & Dò Trùng Lặp (Ticket Creation & Duplicate Check)

Sơ đồ thể hiện quy trình khi người dùng tạo vé sự cố mới từ giao diện Web Portal, lưu trữ dữ liệu vào SQLite và kiểm tra trùng lặp qua ChromaDB.

```mermaid
sequenceDiagram
    actor Employee as 👤 Employee
    participant UI as 🌐 Web Frontend (Ticket Portal)
    participant API as 🚀 FastAPI Backend (/api/v1/tickets)
    participant DB as 🗄️ SQLite Database
    participant Embed as ⚡ Embedding Service
    participant Chroma as 📦 ChromaDB (ticket_duplicates)

    Employee->>UI: 1. Gửi thông tin sự cố (title, description)
    UI->>API: 2. POST /api/v1/tickets (Bearer JWT)
    API->>DB: 3. Lưu bản ghi ticket mới (Status: OPEN)

    API->>Embed: 4. Sinh vector cho sự cố mới
    Embed-->>API: 5. Vector 384 chiều
    API->>Chroma: 6. Vector search tìm vé tương tự (collection: ticket_duplicates)
    Chroma-->>API: 7. Trả về danh sách vé tương tự (nếu có)

    alt Phát hiện vé tương tự (> configurable threshold)
        API->>DB: 8a. Gắn cờ potential_duplicate_of
    end

    API-->>UI: 9. Trả về mã vé (INC-2026-xxxx)
    UI-->>Employee: 10. Hiển thị thông báo tạo vé thành công
```

---

## 2. Giai Đoạn 2: Xử Lý Phân Loại & Đề Xuất Giải Pháp (AI Triage Processing)

Sơ đồ quy trình xử lý nền của tác nhân **LangGraph Agent** đối với vé sự cố vừa tạo.

```mermaid
sequenceDiagram
    participant API as 🚀 FastAPI Background Task
    participant Agent as 🕸️ LangGraph Agent
    participant LLM as 🧠 Configured LLM Provider
    participant Embed as ⚡ Embedding Service
    participant Chroma as 📦 ChromaDB (helpdesk_kb)
    participant DB as 🗄️ SQLite Database
    actor Reviewer as 👨‍💻 Technician / Manager / Admin

    API->>Agent: 1. Kích hoạt process_ticket(ticket_id)
    Agent->>Agent: 2. Kiểm tra Input Guardrail

    alt Phát hiện vi phạm an toàn / Prompt Injection
        Agent->>DB: 3a. Ghi guardrail event, dừng AI processing và giữ trạng thái theo policy
    else Yêu cầu mô tả quá ngắn / Mơ hồ
        Agent->>DB: 3b. Cập nhật Status: OPEN kèm yêu cầu bổ sung thông tin
    else Yêu cầu hợp lệ
        Agent->>LLM: 4. Đề xuất Category & Urgency
        LLM-->>Agent: 5. Kết quả phân loại cấu trúc
        Agent->>Agent: 6. Tính toán Priority & SLA Deadline theo Policy

        Agent->>Embed: 7. Sinh vector truy vấn RAG
        Embed-->>Agent: 8. Query vector
        Agent->>Chroma: 9. Tìm kiếm tài liệu RAG phù hợp (Top-K)
        Chroma-->>Agent: 10. Bằng chứng tài liệu KB & Runbook

        Agent->>LLM: 11. Tổng hợp giải pháp có căn cứ (Grounded Generation)
        LLM-->>Agent: 12. Dự thảo giải pháp kèm nguồn tham chiếu [SOURCE_ID]

        Agent->>Chroma: 13. Ghi vector ticket vào collection ticket_duplicates

        Agent->>Agent: 14. Đánh giá Confidence/Risk Threshold

        alt Rủi ro thấp & Điểm tin cậy cao
            Agent->>DB: 15a. Cập nhật Status: RESOLVED, lưu suggested_solution
        else Rủi ro cao & Đã có đề xuất giải pháp
            Agent->>DB: 15b. Cập nhật Status: PENDING_HITL
            Note over DB,Reviewer: Dashboard truy vấn danh sách qua GET /api/v1/tickets/pending-hitl
        else Thiếu tài liệu KB / Độ tin cậy thấp
            Agent->>DB: 15c. Cập nhật Status: IN_PROGRESS (Chuyển Kỹ thuật viên)
        end
    end
```

---

## 3. Quy Ước Vòng Đời Chuyển Trạng Thái Vé

Hệ thống quản lý trạng thái vé theo các chuyển dịch hợp lệ đầy đủ (Non-linear state transitions):
- **`OPEN → RESOLVED`:** Tự động giải quyết khi rủi ro thấp và điểm tin cậy cao.
- **`OPEN → PENDING_HITL`:** Chờ duyệt khi phát hiện hành động rủi ro cao nhưng đã có đề xuất giải pháp.
- **`OPEN → IN_PROGRESS`:** Chuyển Kỹ thuật viên xử lý khi thiếu tài liệu KB hoặc điểm tin cậy thấp.
- **`PENDING_HITL → RESOLVED | IN_PROGRESS`:** Duyệt thành công hoặc chuyển Kỹ thuật viên xử lý thủ công.
- **`IN_PROGRESS → RESOLVED`:** Kỹ thuật viên hoàn tất khắc phục sự cố kỹ thuật.
- **`RESOLVED → CLOSED`:** Đóng vé sau khi người dùng xác nhận kết quả trên hệ thống.
