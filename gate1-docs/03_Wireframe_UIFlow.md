# WIREFRAME / UI FLOW

## AI Agent Phân loại & Xử lý Ticket IT Help Desk (ITSM Triage Agent)

**Phiên bản:** 1.0 | **Ngày:** 30/07/2026
**Hình thức:** Web App độc lập (Single Web Application), xây dựng bằng **Next.js** — dashboard cho Agent (IT Support/Admin) + hàng đợi ticket, có phân chia rõ theo vai trò (End User vs. IT Support/Admin) trên cùng một ứng dụng

---

## 1. Đối tượng sử dụng (Personas)

| Persona                           | Vai trò trên UI                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| **End User**                | Nhân viên công ty thành viên — tạo & theo dõi ticket                                  |
| **IT Support Agent**        | Xử lý ticket được định tuyến; xử lý ticket có độ tin cậy thấp; xác nhận HITL |
| **KB Manager** (IT Support) | Thêm/sửa/xóa tài liệu Knowledge Base                                                     |
| **Admin**                   | Xem dashboard giám sát toàn hệ thống, cấu hình ngưỡng, phân quyền                  |

## 2. Sơ đồ màn hình (Sitemap)

```
Web App (đăng nhập chung, phân quyền theo role)
│
├── [End User]
│   ├── 1. Dashboard cá nhân (danh sách ticket của tôi)
│   ├── 2. Tạo ticket mới
│   ├── 3. Chi tiết ticket (trạng thái, giải pháp gợi ý, phản hồi)
│
├── [IT Support Agent]
│   ├── 4. Hàng đợi ticket (theo nhóm kỹ thuật / HITL / độ tin cậy thấp)
│   ├── 5. Chi tiết & xử lý ticket (xem phân loại AI, xác nhận/điều chỉnh, đóng ticket)
│   ├── 6. Quản lý Knowledge Base (danh sách, thêm/sửa/xóa tài liệu)
│
├── [Admin]
│   ├── 7. Dashboard giám sát (SLA, Accuracy/F1, chi phí token, volume)
│   ├── 8. Cấu hình hệ thống (ngưỡng tin cậy, ngân sách token, nhóm kỹ thuật, RBAC)
│   ├── 9. Audit Log Viewer
│
└── 10. Đăng nhập / Phân quyền theo company & department
```

## 3. Luồng nghiệp vụ chính (User Flows)

### 3.1. Luồng tạo & xử lý ticket (tổng quan end-to-end)

```
[End User tạo ticket]
        │
        ▼
[AI Agent phân loại: category / priority / urgency + confidence score]
        │
        ▼
   ┌────────────────────────────┐
   │ Confidence ≥ 75%?           │
   └────────────────────────────┘
     │YES                    │NO
     ▼                       ▼
[Kiểm tra điều kiện        [Confidence 60–74%?]
 auto-close/routing]         │YES              │NO (<60%)
     │                       ▼                  ▼
     ▼                [Cảnh báo độ tin cậy   [Bắt buộc chuyển
[Production-critical    thấp — End User      cho IT Support xử lý
 hoặc VIP?]              CHỌN: gửi người      thủ công]
     │YES        │NO      hay giữ nguyên]
     ▼            ▼             │
[HITL: chờ    [Auto-close       ▼
 IT Support    hoặc Route   [Vào hàng đợi IT Support]
 xác nhận]     tự động]
     │
     ▼
[IT Support xác nhận / điều chỉnh]
     │
     ▼
[Ticket đóng — Audit log ghi nhận toàn bộ bước]
```

### 3.2. Luồng quản lý Knowledge Base (IT Support)

```
[IT Support vào "Quản lý KB"]
        │
        ▼
[Xem danh sách tài liệu (PDF/Word) theo category]
        │
   ┌────┴────┬─────────┐
   ▼         ▼         ▼
[Thêm mới] [Sửa/Cập  [Xóa (soft-delete,
 (upload    nhật      có audit log)]
 file +     phiên
 gắn tag)   bản]
        │
        ▼
[Hệ thống tự động index nội dung cho AI Agent truy vấn (RAG)]
```

### 3.3. Luồng giám sát của Admin

```
[Admin đăng nhập] ──> [Dashboard giám sát]
        │
        ├──> Xem SLA compliance theo priority/công ty
        ├──> Xem Accuracy/F1 phân loại theo thời gian
        ├──> Xem chi phí token (ngày/tháng, theo công ty)
        ├──> Xem số ticket đang chờ HITL
        └──> Vào Audit Log Viewer để tra cứu chi tiết hành động
```

## 4. Mô tả Wireframe từng màn hình chính

### Màn hình 1 — Dashboard cá nhân (End User)

```
┌──────────────────────────────────────────────────┐
│ [Logo]     ITSM Help Desk         [Tên user ▾]    │
├──────────────────────────────────────────────────┤
│  [+ Tạo ticket mới]                               │
│                                                    │
│  Ticket của tôi                                   │
│  ┌────────────────────────────────────────────┐  │
│  │ #ID | Tiêu đề | Trạng thái | Priority | Ngày│  │
│  │ 1023| Lỗi VPN | Đang xử lý | High     | ...  │  │
│  │ 1020| Cài PM  | Đã đóng    | Low      | ...  │  │
│  └────────────────────────────────────────────┘  │
│  [Lọc theo trạng thái ▾]  [Tìm kiếm 🔍]           │
└──────────────────────────────────────────────────┘
```

### Màn hình 2 — Tạo ticket mới (End User)

```
┌──────────────────────────────────────────────────┐
│  Tạo Ticket Mới                          [Hủy][Gửi]│
├──────────────────────────────────────────────────┤
│  Tiêu đề: [______________________________]        │
│  Mô tả chi tiết:                                   │
│  [                                            ]    │
│  [                                            ]    │
│  Đính kèm file: [Chọn file...]                     │
│  Công ty thành viên: (tự động theo tài khoản)      │
│  Phòng ban: (tự động theo tài khoản)               │
└──────────────────────────────────────────────────┘
```

### Màn hình 3 — Chi tiết ticket (End User)

```
┌──────────────────────────────────────────────────┐
│  Ticket #1023 — Lỗi kết nối VPN                    │
│  Trạng thái: Đang xử lý | Priority: High           │
├──────────────────────────────────────────────────┤
│  Mô tả ban đầu: "..."                              │
│                                                     │
│  💡 Giải pháp gợi ý từ AI Agent:                   │
│  "..." (Nguồn: KB-Network-05.pdf)                  │
│  Độ tin cậy: 82%                                   │
│                                                     │
│  [Đánh dấu Đã giải quyết]  [Chưa giải quyết →     │
│   gửi lại cho IT Support]                          │
│                                                     │
│  Lịch sử xử lý (timeline) ▾                        │
└──────────────────────────────────────────────────┘
```

### Màn hình 4 — Hàng đợi ticket (IT Support Agent)

```
┌──────────────────────────────────────────────────┐
│ Hàng đợi ticket   [Nhóm: Network ▾] [HITL] [Thấp☹]│
├──────────────────────────────────────────────────┤
│ #ID | Tiêu đề | AI đề xuất | Confidence | Priority│
│ 1023| Lỗi VPN | Network    | 82%  ✅    | High    │
│ 1031| App lỗi | ??         | 55%  ⚠️LOW | Medium  │
│ 1035| SX login| Security   | 68%⚠️(có   │ High    │
│      |        |            |  thể chọn HITL)│      │
├──────────────────────────────────────────────────┤
│ Tab: [Chờ xác nhận HITL] [Độ tin cậy thấp] [Tất cả]│
└──────────────────────────────────────────────────┘
```

### Màn hình 5 — Xử lý ticket (IT Support Agent)

```
┌──────────────────────────────────────────────────┐
│ Ticket #1035 — Không đăng nhập được hệ thống SX    │
│ ⚠️ Confidence: 68% (Cảnh báo độ tin cậy thấp)      │
│ 🏷 Production-critical: Có   🏷 VIP: Không          │
├──────────────────────────────────────────────────┤
│ Phân loại AI đề xuất:                              │
│ Category: [Security ▾]  Priority: [High ▾]         │
│ Urgency: [High ▾]                                  │
│                                                     │
│ Giải pháp gợi ý từ KB: "..." (nguồn: ...)           │
│                                                     │
│ [✔ Xác nhận & Đóng ticket]                         │
│ [✔ Xác nhận & Định tuyến tới nhóm khác]             │
│ [✎ Điều chỉnh phân loại thủ công]                   │
│                                                     │
│ (Ghi chú: Ticket này rơi vào dải cảnh báo 60–74%    │
│  (FR-09) VÀ đồng thời yêu cầu HITL bắt buộc do      │
│  Production-critical = Có (FR-08) — đây là 2 điều   │
│  kiện độc lập, cùng dẫn đến việc cần con người xử lý)│
└──────────────────────────────────────────────────┘
```

### Màn hình 6 — Quản lý Knowledge Base (IT Support)

```
┌──────────────────────────────────────────────────┐
│  Quản lý Knowledge Base        [+ Thêm tài liệu]  │
├──────────────────────────────────────────────────┤
│ Tên file       | Loại | Category | Version | Actions│
│ KB-Network-05  | PDF  | Network  | v2      |✎ 🗑    │
│ KB-Account-02  | DOCX | Account  | v1      |✎ 🗑    │
├──────────────────────────────────────────────────┤
│ [Lọc theo category ▾]   [Tìm kiếm 🔍]              │
└──────────────────────────────────────────────────┘
```

### Màn hình 7 — Dashboard giám sát (Admin)

```
┌──────────────────────────────────────────────────┐
│  Dashboard Giám sát Hệ thống                       │
├──────────────────────────────────────────────────┤
│ [Tổng ticket hôm nay: 342] [SLA vi phạm: 12]       │
│ [Accuracy/F1 (7 ngày): 81.4%] [Chi phí token: $xx] │
│                                                     │
│  📊 Biểu đồ Accuracy/F1 theo thời gian              │
│  📊 Biểu đồ khối lượng ticket theo công ty thành   │
│      viên / theo priority                          │
│  📋 Danh sách ticket đang chờ HITL                  │
│  📋 Ticket có confidence thấp (<60%) chưa xử lý     │
├──────────────────────────────────────────────────┤
│  [Xem Audit Log] [Cấu hình hệ thống]               │
└──────────────────────────────────────────────────┘
```

### Màn hình 8 — Cấu hình hệ thống (Admin)

```
┌──────────────────────────────────────────────────┐
│  Cấu hình hệ thống                                 │
├──────────────────────────────────────────────────┤
│ Ngưỡng độ tin cậy:                                 │
│   Cảnh báo thấp: [75]%   Bắt buộc chuyển người:[60]%│
│ Ngân sách token: [___________] / tháng             │
│ Danh sách nhóm kỹ thuật: [Quản lý danh sách...]     │
│ Tiêu chí Production-critical / VIP: [Cấu hình...]   │
│ Phân quyền (RBAC): [Quản lý user & role...]         │
└──────────────────────────────────────────────────┘
```

### Màn hình 9 — Audit Log Viewer (Admin)

```
┌──────────────────────────────────────────────────┐
│  Audit Log                                         │
├──────────────────────────────────────────────────┤
│ Thời gian | Ticket | Actor      | Hành động        │
│ 10:32     | #1023  | AI Agent   | Phân loại: Network│
│ 10:33     | #1023  | AI Agent   | Auto-close (82%)  │
│ 09:15     | #1035  | IT Support | Xác nhận HITL     │
├──────────────────────────────────────────────────┤
│ [Lọc theo ticket/actor/thời gian]                  │
└──────────────────────────────────────────────────┘
```
