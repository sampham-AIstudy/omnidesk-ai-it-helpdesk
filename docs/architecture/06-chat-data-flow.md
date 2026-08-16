# D2 — Realtime Chat Data Flow (Luồng Dữ Liệu Hội Thoại Trực Tiếp)

> **Tài liệu bổ sung:** Sơ đồ này làm rõ một phần của kiến trúc MVP P-236. Nội dung có thể được điều chỉnh trong quá trình tiếp tục tích hợp và không đại diện cho kiến trúc production cuối cùng.
>
> `Core MVP` biểu thị thành phần thuộc phạm vi MVP, không mặc định rằng thành phần đã hoàn thiện hoặc được xác minh end-to-end.

---

## 1. Sơ Đồ D2: Realtime Streaming Chat Data Flow

Sơ đồ thể hiện quy trình khi người dùng gửi tin nhắn qua giao diện Web Chatbot (HTTPS POST tới `/api/v1/chat/stream`) và máy chủ FastAPI trả về luồng phản hồi dạng **Server-Sent Events (`text/event-stream`)**.

```mermaid
sequenceDiagram
    actor User as 👤 Employee
    participant UI as 🌐 Web Frontend (Chatbot Workspace)
    participant API as 🚀 Chat API Gateway (/api/v1/chat/stream)
    participant Guard as 🛡️ Safety & Abuse Guard
    participant DB as 🗄️ SQLite Database<br/>(chat_conversations + chat_messages)
    participant Embed as ⚡ Embedding Service
    participant Chroma as 📦 ChromaDB Vector Store
    participant Web as 🌐 Web Search Gate (Optional Fallback)
    participant LLM as 🧠 LLM Streaming Engine

    User->>UI: 1. Nhập câu hỏi và gửi tin nhắn
    UI->>API: 2. POST /api/v1/chat/stream (message, conversation_id, Bearer JWT)
    API->>API: 3. Xác thực JWT & Quyền hạn người dùng

    API->>Guard: 4. Kiểm tra Input Guardrail (Prompt Injection / PII)
    Guard-->>API: 5. Kết quả kiểm tra (ALLOWED / BLOCKED)

    break Kết quả BLOCKED
        API-->>UI: Stream thông báo từ chối an toàn & Đóng kết nối
        UI-->>User: Hiển thị cảnh báo vi phạm chính sách
    end

    API->>DB: 6. Lấy lịch sử hội thoại gần nhất (chat_messages)
    DB-->>API: 7. Ngữ cảnh hội thoại trước đó

    API->>Embed: 8. Vectorize câu hỏi hội thoại (384-dim)
    Embed-->>API: 9. Query vector
    API->>Chroma: 10. Truy vấn vector tài liệu tri thức (Top-K)
    Chroma-->>API: 11. Trả về các đoạn tài liệu phù hợp

    alt Điểm tin cậy RAG thấp & Cần tra cứu bổ trợ
        API->>Web: 12a. Tìm kiếm thông tin ngoài (Đã lọc PII)
        Web-->>API: 12b. Kết quả tìm kiếm (Dữ liệu không tin cậy)
        API->>API: 12c. Kiểm tra & Khử độc nội dung web trước khi đưa vào prompt
    end

    API->>LLM: 13. Gửi Prompt hệ thống (Context + Bằng chứng + Câu hỏi)

    loop Stream Token Từng Phần (text/event-stream)
        LLM-->>API: 14a. Chunk token văn bản
        API->>Guard: 14b. Kiểm tra an toàn nội dung phản hồi
        Guard-->>API: 14c. Nội dung đã kiểm tra
        API-->>UI: 14d. event: "token", data: {"text": "..."}
        UI-->>User: 14e. Hiển thị chữ xuất hiện thời gian thực
    end

    API->>DB: 15. Lưu tin nhắn người dùng và phản hồi của AI vào bảng chat_messages
    API-->>UI: 16. event: "sources", data: [{"id": "kb-xxx", "title": "..."}]
    API-->>UI: 17. event: "done", data: {"status": "completed"}
    UI-->>User: 18. Hoàn tất lượt trả lời & Hiển thị thẻ trích dẫn nguồn
```

---

## 2. Các Biện Pháp An Toàn Trong Luồng Chat

1. **Xác thực trước khi xử lý (*Auth Pre-check*):** Mọi request tới `/api/v1/chat` hoặc `/api/v1/chat/stream` đều bắt buộc phải mang theo JWT Token hợp lệ để định danh người dùng.
2. **Khử nhiễm dữ liệu ngoài (*Web Sanitization*):** Dữ liệu tra cứu từ Internet được coi là dữ liệu thô chưa kiểm chứng (*Untrusted Content*), luôn được bóc tách và lọc thẻ độc hại trước khi đưa vào ngữ cảnh LLM.
3. **Kiểm soát an toàn nội dung (*Output Guardrail*):** Hệ thống thực hiện rà soát an toàn nội dung trước hoặc trong quá trình trả phản hồi, nhằm phát hiện và che giấu các mẫu thông tin nhạy cảm như mật khẩu, khóa API hoặc số điện thoại.
