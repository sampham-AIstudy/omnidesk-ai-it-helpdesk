# PRD (Product Requirements Document)

## AI Agent Phân loại & Xử lý Ticket IT Help Desk

**Phiên bản:** 1.0 | **Ngày:** 30/07/2026

---

## 1. Tổng quan sản phẩm

Xây dựng mới hoàn toàn một Web App độc lập, nơi:

- Nhân viên của các công ty thành viên gửi và theo dõi ticket IT của mình.
- Đội IT Support xử lý ticket, quản lý Knowledge Base (KB), và can thiệp khi AI Agent cần HITL.
- AI Agent đọc ticket, phân loại, gợi ý giải pháp từ KB, tự đóng ticket đơn giản hoặc định tuyến ticket đến đúng nhóm kỹ thuật, theo dõi SLA và leo thang khi cần.

## 2. Đối tượng người dùng (Actors)

| Actor                                    | Mô tả                                                                                                                     |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **End User**                       | Nhân viên các công ty thành viên — tạo ticket, theo dõi trạng thái ticket của mình                             |
| **IT Support Agent**               | Xử lý ticket được định tuyến đến nhóm mình; xử lý ticket có độ tin cậy phân loại thấp; xác nhận HITL |
| **KB Manager** (thuộc IT Support) | Thêm/sửa/xóa tài liệu Knowledge Base (PDF, Word)                                                                       |
| **Admin (Super Admin)**            | Quản trị hệ thống, phân quyền, giám sát dashboard, cấu hình ngưỡng tin cậy, ngân sách token                  |
| **AI Agent (hệ thống)**          | Actor tự động: phân loại, gợi ý giải pháp, auto-close, routing, escalation                                         |

## 3. Tech Stack & Kiến trúc tổng quan

### 3.1. Tech Stack

| Thành phần                    | Công nghệ                                                                                                                                                    |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM                             | GPT-4o hoặc Claude                                                                                                                                            |
| Điều phối Agent              | LangGraph (orchestration cho pipeline: phân loại -> RAG -> confidence scoring -> HITL/routing/escalation)                                                    |
| RAG / Vector DB                 | Qdrant hoặc pgvector - index nội dung Knowledge Base (PDF/Word)                                                                                              |
| Classifier & Confidence Scoring | Module phân loại category/priority/urgency kèm điểm tin cậy, tích hợp trong pipeline LangGraph                                                         |
| API ITSM                        | REST API tự xây, mô phỏng theo chuẩn ServiceNow/Jira Service Management                                                                                  |
| Backend                         | FastAPI (Python)                                                                                                                                               |
| Frontend                        | Next.js - dashboard cho Agent (IT Support/Admin) + hàng đợi ticket, có phân theo vai trò người dùng (End User) và agent hỗ trợ (IT Support/Admin) |
| Observability                   | LangSmith hoặc Langfuse - theo dõi trace, chi phí token, hiệu năng của LLM/Agent pipeline                                                               |
| Triển khai (Deploy)            | Frontend: Vercel, Backend: Render hoặc Railway.                                                                                                              |

### 3.2. Kiến trúc tổng quan (mức cao)

```
 [End User - Next.js Web] ──┐
                            ├──> [Frontend Next.js: Dashboard + Hàng đợi ticket
[IT Support/Admin -         │      (phân theo vai trò)]
 Next.js Web]     ──────────┘                │
                                              ▼
                              [Backend FastAPI: REST API mô phỏng
                               chuẩn ServiceNow/Jira]
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                [Database: Ticket,   [ITSM Triage Agent      [Observability:
                 KB metadata, User,   — LangGraph]             LangSmith/Langfuse]
                 Audit Log, SLA,            │
                 Token Usage]               ├──> LLM (GPT-4o/Claude): phân loại
                                            ├──> Classifier + Confidence Scoring
                                            ├──> RAG (Qdrant/pgvector) trên KB (PDF/Word)
                                            ├──> HITL Trigger
                                            └──> Routing/Escalation Engine
```

**Deploy:** Frontend (Next.js) → Vercel | Backend (FastAPI + Agent) → Render/Railway.

## 4. Yêu cầu chức năng chi tiết

### 4.1. Quản lý Ticket

**FR-01 — Tạo ticket (End User)**

- End User đăng nhập, tạo ticket mới với: tiêu đề, mô tả chi tiết, đính kèm file (tùy chọn), công ty thành viên (tự động theo tài khoản), phòng ban.
- Ticket được gán mã số tự động và trạng thái ban đầu `New`.

**FR-02 — Theo dõi ticket (End User)**

- Xem danh sách ticket của bản thân, trạng thái, lịch sử xử lý, giải pháp được gợi ý/áp dụng.

**FR-03 — Xử lý ticket (IT Support)**

- Xem danh sách ticket được định tuyến đến nhóm mình.
- Xem kết quả phân loại của AI Agent (category, priority, urgency, độ tin cậy).
- Xác nhận/điều chỉnh phân loại, xác nhận HITL, cập nhật trạng thái, đóng ticket.

### 4.2. AI Agent — Phân loại & Xử lý tự động

**FR-04 — Phân loại ticket**

- Agent đọc mô tả ticket và trả về: `category`, `priority`, `urgency`, kèm **confidence score** (%).

**FR-05 — Gợi ý giải pháp từ Knowledge Base**

- Agent truy vấn KB (RAG trên tài liệu PDF/Word đã được IT Support upload) để gợi ý giải pháp phù hợp nhất, kèm trích dẫn nguồn tài liệu.

**FR-06 — Tự động đóng ticket (Auto-close)**

- Nếu ticket được phân loại là đơn giản, có giải pháp KB rõ ràng, và **độ tin cậy ≥ 75%** (xem bảng ngưỡng chuẩn tại FR-09) **và không thuộc diện HITL bắt buộc** (xem FR-08), agent có thể tự động đóng ticket kèm giải pháp.
- Ticket tự đóng vẫn cho phép End User phản hồi "Chưa giải quyết" để mở lại.

**FR-07 — Định tuyến ticket (Routing)**

- Ticket không thể tự đóng sẽ được định tuyến đến đúng nhóm kỹ thuật phụ trách dựa trên category.

**FR-08 — Human-in-the-Loop (HITL) bắt buộc**

Bắt buộc có xác nhận của IT Support nếu:

- Ticket được agent xử lý có độ tin cậy < 60%
- Tự động đóng ticket, hoặc tự động định tuyến ticket nếu ticket được đánh dấu ảnh hưởng đến hệ thống production hoặc thuộc người dùng VIP.

**FR-09 — Ngưỡng độ tin cậy phân loại**

Cơ chế 3 dải ngưỡng (thay thế mọi mô tả mơ hồ khác trong tài liệu — đây là bảng chuẩn duy nhất):

| Ngưỡng Confidence | Hành vi hệ thống                                                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ≥ 75%              | Xử lý bình thường (agent có thể tự phân loại/gợi ý/auto-close nếu đủ điều kiện, và không thuộc diện HITL bắt buộc theo FR-08)  |
| 60% – 74%          | **Cảnh báo độ tin cậy thấp**; hệ thống cho End User **tùy chọn** gửi ticket cho người xử lý trực tiếp (không bắt buộc) |
| < 60%               | **Bắt buộc** gửi ticket cho IT Support xử lý thủ công (không cho agent tự đóng/định tuyến tự động)                              |

**FR-10 — Leo thang SLA (Escalation)**

- Hệ thống theo dõi thời gian xử lý ticket theo SLA gắn với priority.
- Khi ticket có nguy cơ/đã vi phạm SLA, hệ thống tự động leo thang (thông báo cấp quản lý, tăng priority, hoặc điều chuyển).

### 4.3. Quản lý Knowledge Base

**FR-11 — Thêm/Sửa/Xóa tài liệu KB (IT Support)**

- IT Support upload tài liệu KB dạng **PDF hoặc Word**, gắn tag/category liên quan.
- Sửa/cập nhật phiên bản, xóa (soft-delete có audit log).
- Hệ thống tự động index nội dung tài liệu để phục vụ truy vấn RAG cho AI Agent (FR-05).

### 4.4. Phân quyền (RBAC) (Dự định)

| Role                                                      | Phạm vi truy cập                                                                                                            | Quyền chính                                                                                      |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **End User**                                        | Chỉ ticket của chính mình, trong công ty thành viên của mình                                                         | Tạo/xem/phản hồi ticket của bản thân                                                         |
| **IT Support Agent**                                | Ticket thuộc nhóm kỹ thuật được phân công, trên toàn bộ công ty thành viên (hoặc giới hạn theo phân công) | Xử lý, cập nhật, đóng ticket; xác nhận HITL                                                |
| **KB Manager**                                      | Toàn bộ Knowledge Base                                                                                                      | Thêm/sửa/xóa tài liệu KB                                                                      |
| **Company Admin** *(đề xuất, cần xác nhận)* | Ticket trong phạm vi công ty thành viên mình quản lý                                                                   | Xem báo cáo, giám sát ticket của công ty mình                                               |
| **Super Admin**                                     | Toàn hệ thống                                                                                                              | Cấu hình ngưỡng tin cậy, ngân sách token, phân quyền, xem toàn bộ audit log & dashboard |

- Phân quyền áp dụng theo 2 chiều: theo công ty thành viên (tenant/company_id) và theo phòng ban/nhóm kỹ thuật.
- Đề xuất mô hình dữ liệu: mỗi user có `company_id`, `department_id`, `role`, và (với IT Support) `technical_group_id`.

### 4.5. Audit Log

**FR-12 — Ghi log mọi hành động**

- Mọi hành động trên ticket (tạo, phân loại AI, thay đổi trạng thái, HITL xác nhận, auto-close, routing, escalation, sửa bởi người dùng) đều được ghi log với: thời gian, actor (người/agent), hành động, dữ liệu trước/sau.
- Log không thể chỉnh sửa/xóa (immutable), chỉ Super Admin có quyền xem toàn bộ.

### 4.6. Kiểm soát chi phí token

**FR-13 — Theo dõi & giới hạn chi phí**

- Hệ thống theo dõi số token tiêu thụ mỗi lần gọi AI Agent (phân loại + RAG).
- Hiển thị chi phí tích lũy trên dashboard (theo ngày/tháng, theo công ty thành viên nếu cần).

### 4.7. Dashboard giám sát

**FR-14 — Dashboard cho Admin/IT Support**

- Theo dõi: số lượng ticket theo trạng thái/priority/công ty thành viên, tỷ lệ vi phạm SLA, Accuracy/F1 phân loại theo thời gian, chi phí token, số ticket cần HITL đang chờ xử lý.

## 5. Yêu cầu phi chức năng (Non-functional Requirements)

| Loại                | Yêu cầu                                                                                                                                                                       |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hiệu năng          | Phân loại ticket trả kết quả trong thời gian hợp lý (đề xuất < 10s/ticket — cần xác nhận SLA kỹ thuật)                                                         |
| Bảo mật            | Phân quyền RBAC chặt chẽ theo company/department; mã hóa dữ liệu nhạy cảm                                                                                             |
| Khả năng mở rộng | Có thể thêm công ty thành viên mới, nhóm kỹ thuật mới mà không cần sửa code                                                                                      |
| Độ tin cậy        | Audit log không được mất dữ liệu (immutable, có backup)                                                                                                                 |
| Khả năng quan sát | Dashboard theo dõi real-time hoặc near real-time; toàn bộ pipeline Agent (LangGraph) được trace qua LangSmith/Langfuse để debug và theo dõi chi phí/hiệu năng LLM |

## 6. Mô hình dữ liệu sơ bộ (Entities chính)

- **User** (id, name, email, role, company_id, department_id, technical_group_id)
- **Company** (id, name) — công ty thành viên
- **Ticket** (id, title, description, category, priority, urgency, confidence_score, status, is_production_critical, is_vip, created_by, assigned_group, created_at, sla_due_at)
- **KnowledgeDocument** (id, file_name, file_type, category_tags, uploaded_by, version, status) — nội dung được chunk & embed vào **Qdrant/pgvector** để phục vụ RAG
- **AuditLog** (id, ticket_id, actor_type, actor_id, action, before_state, after_state, timestamp)
- **TokenUsageLog** (id, ticket_id, tokens_used, cost, model, timestamp) — dữ liệu có thể đối chiếu với trace từ LangSmith/Langfuse
