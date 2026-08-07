# PROJECT BRIEF

## AI Agent Phân loại & Xử lý Ticket IT Help Desk (ITSM Triage Agent)

**Ngày tạo:** 30/07/2026
**Phiên bản:** 1.0

---

## 1. Tóm tắt thực trạng

Bộ phận Help Desk của tập đoàn hiện đang tiếp nhận hàng nghìn ticket mỗi ngày từ nhân viên của nhiều công ty thành viên (ví dụ: Doanh nghiệp Bất động sản X, Xe X, Hệ thống Y tế X...). Quy trình phân loại và định tuyến ticket hiện tại được thực hiện **thủ công**, dẫn đến:

- Thời gian phản hồi (response time) chậm, không đáp ứng kỳ vọng của người dùng cuối.
- Nguy cơ phân loại sai mức độ ưu tiên (priority) và định tuyến nhầm nhóm kỹ thuật.
- Tải công việc lặp lại cho đội IT Support với các ticket đơn giản, lặp lại, có thể tự động hóa.
- Thiếu cơ chế giám sát/leo thang khi ticket vi phạm SLA.

## 2. Vấn đề cần giải quyết

Xây dựng một **AI Agent** có khả năng:

1. Tự động đọc và hiểu mô tả ticket do người dùng gửi lên.
2. Phân loại ticket theo **category / priority / urgency**.
3. Gợi ý giải pháp dựa trên **Knowledge Base (KB)** nội bộ.
4. Tự động đóng (auto-close) các ticket đơn giản, có độ tin cậy phân loại cao.
5. Định tuyến các ticket phức tạp đến đúng nhóm kỹ thuật phụ trách.
6. Giám sát và leo thang (escalate) khi ticket có nguy cơ vi phạm SLA.

## 3. Ràng buộc dự án

| Nhóm ràng buộc                        | Nội dung                                                                                                                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Human-in-the-Loop (HITL)**       | Bắt buộc có sự xác nhận của con người trước khi agent tự đóng hoặc định tuyến ticket ảnh hưởng đến hệ thống production hoặc ticket của người dùng VIP. |
| **Phân quyền**                   | Phân quyền truy cập theo công ty thành viên và theo phòng ban.                                                                                                               |
| **Chất lượng phân loại**      | Đo lường bằng chỉ số Accuracy/F1-score; mục tiêu ≥ 80%.                                                                                                                     |
| **Audit log**                      | Ghi log toàn bộ hành động của agent và người dùng trên từng ticket.                                                                                                      |
| **Cảnh báo độ tin cậy thấp** | Khi độ tin cậy phân loại thấp, hệ thống phải cảnh báo và điều hướng theo ngưỡng quy định.                                                                        |
| **Kiểm soát chi phí token**     | Cần cơ chế theo dõi và giới hạn chi phí gọi model AI.                                                                                                                       |

## 4. Timeline dự án (Cần golden test cho từng giai đoạn)

**Tổng thời gian: 6 tuần**

| Tuần   | Giai đoạn                        | Nội dung chính                                                                                                              |
| ------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Tuần 1 | Khởi tạo & Thiết kế            | Hoàn thiện Brief, PRD, Wireframe/UI Flow, thiết kế kiến trúc hệ thống & data model. TẠO TEST TRONG TỪNG GIAI ĐOẠN |
| Tuần 2 | Xây dựng nền tảng              | Thiết lập hạ tầng web app, database, cơ chế upload/quản lý KB                                                        |
| Tuần 3 | Xây dựng AI Agent - Core         | Xây dựng module phân loại (category/priority/urgency), tích hợp truy vấn KB                                            |
| Tuần 4 | HITL & Routing & SLA               | Xây dựng luồng HITL, cơ chế định tuyến nhóm kỹ thuật, escalation SLA                                               |
| Tuần 5 | Audit log, phân quyền, dashboard | Hoàn thiện RBAC, audit log, dashboard giám sát, kiểm soát chi phí token                                                |
| Tuần 6 | Kiểm thử & Nghiệm thu           | Test end-to-end, đo Accuracy/F1, UAT, hoàn thiện tài liệu, bàn giao                                                     |

## 5. Đội ngũ dự án

Team gồm **3 thành viên**: A, B, C.

- **Nguyễn Việt Anh** — **Team Leader** + AI Agent Engineer: thiết kế orchestration bằng LangGraph, tích hợp LLM (GPT-4o/Claude), xây dựng classifier & confidence scoring, RAG (Qdrant/pgvector) trên Knowledge Base.
- **Nguyễn Trần Nghĩa** — **Backend Engineer**: xây dựng API bằng FastAPI (mô phỏng chuẩn REST ITSM kiểu ServiceNow/Jira), database, HITL/routing/escalation engine, audit log, tích hợp observability (LangSmith/Langfuse). Tích hợp phân quyền theo user, phòng ban
- **Phạm Văn Sâm** — **Frontend Engineer kiêm DevOps**: Cùng các thành viên khác xây dựng database, xây dựng giao diện người dùng, giao diện quản lý Knowledge Base, xây dựng dashboard & hàng đợi ticket, kiểm thử, triển khai.

## 6. Mục tiêu & Chỉ số thành công (KPI)

| Chỉ số                                                             | Mục tiêu                                     |
| -------------------------------------------------------------------- | ---------------------------------------------- |
| Độ chính xác phân loại (Accuracy/F1)                           | ≥ 80%                                         |
| Tỷ lệ ticket tự đóng thành công (không cần can thiệp lại) | Chưa xác định — cần đo baseline sau UAT |
| Thời gian phản hồi trung bình                                    | Chưa có số liệu baseline hiện tại        |
| Tuân thủ HITL cho ticket production/VIP                            | ≥ 80%                                         |
| Audit log coverage                                                   | 100% hành động được ghi log              |

## 7. Phạm vi (Scope) — tóm tắt

**Trong phạm vi (In-scope):**

- Web app độc lập cho việc tạo, quản lý ticket và quản lý Knowledge Base.
- AI Agent phân loại, gợi ý giải pháp, auto-close, routing, escalation.
- HITL workflow, RBAC, audit log, dashboard giám sát, kiểm soát chi phí token.

**Ngoài phạm vi (Out-of-scope):**

- Tích hợp thật với hệ thống ITSM bên thứ ba (ServiceNow/Jira Service Management thật). Dự án chỉ xây dựng **API REST mô phỏng theo chuẩn** của các hệ thống này trên nền hệ thống tự xây mới hoàn toàn.
- Ứng dụng di động (chỉ web app trong giai đoạn này).

## 8. Rủi ro chính

| Rủi ro                                                                                                                     | Mức độ   | Ghi chú                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------- |
| Thời gian 6 tuần khá gấp cho một hệ thống AI Agent + web app + RBAC + audit log đầy đủ, với team chỉ 3 người | Cao         | Cần ưu tiên MVP rõ ràng, cân nhắc cắt giảm phạm vi của đề tài nếu chậm tiến độ |
| Chi phí token vượt kiểm soát nếu không giới hạn ngân sách cụ thể                                               | Trung bình | Ngân sách cụ thể chưa được xác định (xem PRD)                                          |
