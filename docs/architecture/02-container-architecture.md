# C2 — Container Architecture Diagram (Mức 2: Các Khối Ứng Dụng & Hạ Tầng)

> **Tài liệu bổ sung:** Sơ đồ này làm rõ một phần của kiến trúc MVP P-236. Nội dung có thể được điều chỉnh trong quá trình tiếp tục tích hợp và không đại diện cho kiến trúc production cuối cùng.
>
> `Core MVP` biểu thị thành phần thuộc phạm vi MVP, không mặc định rằng thành phần đã hoàn thiện hoặc được xác minh end-to-end.
>
> ONNX Runtime là phương án triển khai hiện tại của Embedding Service, không phải ràng buộc kiến trúc và có thể được thay thế bằng model hoặc provider tương thích.

---

## 1. Sơ Đồ C2: Container Diagram

Sơ đồ phân rã các khối ứng dụng (Containers / Executable Units), kho lưu trữ dữ liệu và các giao thức kết nối trong hệ thống **P-236 MVP**.

```mermaid
graph TB
    subgraph ClientLayer["🖥️ Tầng Trình Duyệt (Client Layer)"]
        Browser["🌐 Web Browser (Desktop / Mobile)"]
    end

    subgraph P236_Containers["🏢 Các Khối Ứng Dụng P-236"]
        subgraph WebContainer["🌐 1. Web Application Container (In Progress)"]
            FrontendApp["Next.js 15 Web Application<br/>• Chatbot Workspace & Ticket Portal<br/>• HITL & Service Request Dashboard<br/>• Tailwind CSS UI System & Client Stores"]
        end

        subgraph BackendContainer["🚪 2. API Gateway & Agent Core (Core MVP)"]
            APIGateway["FastAPI Backend Server<br/>• REST Endpoints & Streaming SSE<br/>• JWT Authentication & RBAC Middleware<br/>• Request Body Size & Safety Interceptors"]

            LangGraphEngine["LangGraph State Machine (In-Process Engine)<br/>• Đồ thị tác nhân StateGraph điều phối quy trình<br/>• Input/Output Guardrails & Classifier<br/>• RAG Retrieval & Risk Assessment Gate"]

            APIGateway --> LangGraphEngine
        end

        subgraph EmbeddingContainer["⚡ 3. Embedding Microservice (Core MVP)"]
            EmbeddingMicroservice["Embedding Service Container<br/>• Dịch vụ vector hóa văn bản (384-dim)<br/>• (Triển khai hiện tại: FastAPI + ONNX Runtime)"]
        end

        subgraph StorageLayer["💾 4. Khối Lưu Trữ Dữ Liệu Bền Vững (Core MVP)"]
            SQLiteDB[("🗄️ SQLite Database (/app/data/helpdesk.db)<br/>• Users, Tickets, Service Requests<br/>• Chat Conversations & Audit Logs<br/>(Truy xuất qua Async SQLAlchemy ORM)")]

            ChromaStore[("📦 ChromaDB Vector Store (/app/data/chroma)<br/>• Collection tài liệu tri thức (helpdesk_kb)<br/>• Collection vé sự cố lịch sử (ticket_duplicates)")]
        end

        subgraph ObservabilityLayer["📊 5. Khối Giám Sát & Đo Đạc (In Progress)"]
            OTelCollector["OpenTelemetry Collector (In Progress)<br/>Thu thập Spans, Traces & Metrics"]
        end
    end

    subgraph ExternalServices["☁️ Dịch Vụ Bên Ngoài (External Services)"]
        LLMProvider["🧠 Configured LLM Provider (Core MVP)<br/>(Một provider cấu hình qua môi trường; fallback khi cần)"]
        WebSearchGate["🌐 Web Search Gate (Optional Fallback)"]
    end

    %% Giao tiếp giữa các thành phần
    Browser -->|HTTPS / JSON / SSE| FrontendApp
    FrontendApp -->|REST API / SSE Streams| APIGateway

    BackendContainer -->|Async SQL Queries| SQLiteDB
    BackendContainer -->|Yêu cầu embedding| EmbeddingMicroservice
    EmbeddingMicroservice -->|Trả vector 384-dim| BackendContainer
    BackendContainer -->|Vector similarity queries| ChromaStore
    BackendContainer -->|LLM Inference Calls| LLMProvider
    BackendContainer -.->|Tra cứu bổ trợ khi KB thiếu| WebSearchGate
    BackendContainer -.->|Gửi telemetry data| OTelCollector
```

---

## 2. Bảng Mô Tả Các Container & Khối Dữ Liệu

| Khối Thành Phần | Công Nghệ / Triển Khai Hiện Tại | Trạng Thái | Vai Trò & Giao Thức Kết Nối |
| :--- | :--- | :---: | :--- |
| **Web Application** | Next.js 15 (React 19, TypeScript) | `In Progress` | Cung cấp giao diện người dùng cho Nhân viên, Kỹ thuật viên, Quản lý và Quản trị viên. Giao tiếp với Backend qua HTTPS REST API và Server-Sent Events (SSE). |
| **API & Agent Core** | FastAPI (Python 3.11, Uvicorn) | `Core MVP` | Máy chủ xử lý nghiệp vụ chính, tiếp nhận API, xác thực quyền hạn và chạy đồ thị tác nhân **LangGraph** (chạy in-process bên trong FastAPI). |
| **Embedding Service** | Triển khai hiện tại: FastAPI + ONNX Runtime | `Core MVP` | Microservice độc lập sinh vector 384 chiều cho câu hỏi và tài liệu tri thức, tách xử lý embedding khỏi backend; có thể thay đổi engine linh hoạt. |
| **Relational Database** | SQLite (`/app/data/helpdesk.db`) | `Core MVP` | Lưu trữ dữ liệu quan hệ có cấu trúc: tài khoản, vé sự cố, yêu cầu dịch vụ, lịch sử hội thoại và bản ghi kiểm toán (*Audit Logs*). |
| **Vector Store** | ChromaDB (`/app/data/chroma`) | `Core MVP` | Lưu trữ và tìm kiếm vector ngữ nghĩa tương đồng cho kho tri thức KB và dò vé trùng lặp. |
| **PostgreSQL / pgvector**| PostgreSQL | `Future Extension` | Mở rộng khả năng lưu trữ và truy vấn vector quy mô lớn khi tải tăng cao. |
| **Observability Stack** | OpenTelemetry | `In Progress` | Thu thập metrics và phân tích luồng thực thi tác nhân AI. |
