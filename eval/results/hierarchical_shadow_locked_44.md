# P-236 Retrieval Evaluation Baseline & Release Gate Report

- **Generated At**: `2026-08-20T16:37:02.208382+00:00`
- **Collection**: `helpdesk_kb_multilingual_v3_hierarchical_shadow`
- **Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Collection Size**: 443 documents/chunks
- **Golden Test Cases**: 44 total (39 scorable)
- **Golden File SHA-256**: `ca55989f841372f7...`
- **Evaluation Mode**: Raw Retriever (`search_similar()`, Top-5)
- **Gate Overall Status**: **✅ PASSED**

## 1. Regression Lock & Quality Metrics

| Metric | Measured Value | Threshold | Status |
|---|---:|---:|:---:|
| **HitRate@1** | 100.0% | >= 97.0% | ✅ PASS |
| **Recall@1** | 97.4% | >= 94.0% | ✅ PASS |
| **HitRate@3** | 100.0% | >= 97.0% | ✅ PASS |
| **Recall@3** | 97.4% | >= 94.0% | ✅ PASS |
| **HitRate@5** | 100.0% | >= 97.0% | ✅ PASS |
| **Recall@5** | 97.4% | >= 94.0% | ✅ PASS |
| **MRR@5** | 1.000 | >= 0.980 | ✅ PASS |
| **nDCG@5** | 0.962 | >= 0.930 | ✅ PASS |
| **D_typo_informal HitRate@1** | 100.0% | >= 90.0% | ✅ PASS |
| **B_exact_token HitRate@1** | 100.0% | >= 95.0% | ✅ PASS |
| **Cross-Tenant Leaks** | 0 | == 0 | ✅ PASS |
| **Forbidden Doc Leaks** | 0 | == 0 | ✅ PASS |
| **Policy Authority Violations** | 0 | == 0 | ✅ PASS |

## 2. Category Breakdown

| Category Group | Cases | Scorable | HitRate@1 | HitRate@5 | Recall@5 | MRR | nDCG@5 | Leaks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A_semantic_paraphrase` | 7 | 7 | 100.0% | 100.0% | 85.7% | 1.000 | 0.907 | 0 |
| `B_exact_token` | 7 | 7 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `C_multilingual` | 5 | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 |
| `D_typo_informal` | 5 | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 |
| `E_ambiguous` | 2 | 0 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `F_policy_authority` | 4 | 4 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `G_tenant_isolation` | 5 | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.985 | 0 |
| `H_no_evidence` | 3 | 0 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `I_hard_negative` | 6 | 6 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 |

## 3. Failure Breakdown

No failures detected across all test cases. ✅

## 4. Case-by-Case Results

| ID | Category | Query | Expected | 1st Hit Rank | Top Retrieved ID & Title | Status |
|---|---|---|---|:---:|---|:---:|
| `RET-A01` | `A_semantic_paraphrase` | VPN của tôi không kết nối được | `kb-001` | 1 | `kb-001` (1.00): Không kết nối được VPN công ty | ✅ PASS |
| `RET-A02` | `A_semantic_paraphrase` | Tôi không truy cập được mạng nội bộ khi  | `kb-001` | 1 | `kb-003` (0.75): Không truy cập được Internet t | ✅ PASS |
| `RET-A03` | `A_semantic_paraphrase` | Máy tính không bắt được WiFi công ty dù  | `kb-002` | 1 | `kb-002` (0.75): WiFi văn phòng yếu/mất kết nối | ✅ PASS |
| `RET-A04` | `A_semantic_paraphrase` | Email bị kẹt trong hộp thư đi không gửi  | `kb-004` | 1 | `kb-004` (0.75): Outlook không đồng bộ email /  | ✅ PASS |
| `RET-A05` | `A_semantic_paraphrase` | Máy tính của tôi chạy rất chậm không làm | `kb-009` | 1 | `kb-009` (0.75): Máy tính chạy chậm / lag | ✅ PASS |
| `RET-A06` | `A_semantic_paraphrase` | Tôi quên mật khẩu đăng nhập Windows khôn | `kb-010` | 1 | `kb-010` (0.75): Quên mật khẩu Windows / tài kh | ✅ PASS |
| `RET-A07` | `A_semantic_paraphrase` | Laptop Windows bị màn hình xanh liên tục | `kb-015` | 1 | `kb-015` (0.94): Laptop hỏng / không khởi động  | ✅ PASS |
| `RET-B01` | `B_exact_token` | FortiClient báo authentication failed kh | `kb-001` | 1 | `kb-001` (1.00): Không kết nối được VPN công ty | ✅ PASS |
| `RET-B02` | `B_exact_token` | BitLocker yêu cầu recovery key khi khởi  | `kb-015` | 1 | `kb-015` (0.75): Laptop hỏng / không khởi động  | ✅ PASS |
| `RET-B03` | `B_exact_token` | Outlook bị Disconnected và email stuck t | `kb-004` | 1 | `kb-004` (1.00): Outlook không đồng bộ email /  | ✅ PASS |
| `RET-B04` | `B_exact_token` | SAP session timeout và bị maximum sessio | `kb-019` | 1 | `kb-019` (1.00): SAP không đăng nhập được / ses | ✅ PASS |
| `RET-B05` | `B_exact_token` | BSOD stop code xuất hiện lúc khởi động W | `kb-015` | 1 | `kb-015` (0.79): Laptop hỏng / không khởi động  | ✅ PASS |
| `RET-B06` | `B_exact_token` | Email phishing yêu cầu nhập thông tin đă | `kb-017` | 1 | `kb-017` (0.75): Nhận email phishing / lừa đảo | ✅ PASS |
| `RET-B07` | `B_exact_token` | Microsoft Authenticator mất điện thoại c | `kb-018` | 1 | `kb-018` (1.00): Yêu cầu reset MFA / 2FA | ✅ PASS |
| `RET-C01` | `C_multilingual` | Cannot connect to company VPN, getting a | `kb-001` | 1 | `kb-001` (0.75): Không kết nối được VPN công ty | ✅ PASS |
| `RET-C02` | `C_multilingual` | Outlook không sync, email stuck trong ou | `kb-004` | 1 | `kb-004` (1.00): Outlook không đồng bộ email /  | ✅ PASS |
| `RET-C03` | `C_multilingual` | Laptop bị blue screen liên tục không biế | `kb-015` | 1 | `kb-015` (0.75): Laptop hỏng / không khởi động  | ✅ PASS |
| `RET-C04` | `C_multilingual` | Password reset cho domain account Window | `kb-010` | 1 | `kb-010` (0.86): Quên mật khẩu Windows / tài kh | ✅ PASS |
| `RET-C05` | `C_multilingual` | WiFi office yeu/ mat ket noi lien tuc | `kb-002` | 1 | `kb-002` (0.77): WiFi văn phòng yếu/mất kết nối | ✅ PASS |
| `RET-D01` | `D_typo_informal` | vpn auth loi ko vao dc | `kb-001` | 1 | `kb-001` (0.80): Không kết nối được VPN công ty | ✅ PASS |
| `RET-D02` | `D_typo_informal` | wifi cty ko vao dc | `kb-002` | 1 | `kb-002` (0.75): WiFi văn phòng yếu/mất kết nối | ✅ PASS |
| `RET-D03` | `D_typo_informal` | outlook ko sync | `kb-004` | 1 | `kb-004` (1.00): Outlook không đồng bộ email /  | ✅ PASS |
| `RET-D04` | `D_typo_informal` | may tinh cham lag qua troi | `kb-009` | 1 | `kb-009` (0.83): Máy tính chạy chậm / lag | ✅ PASS |
| `RET-D05` | `D_typo_informal` | ko nho mat khau may tinh | `kb-010` | 1 | `kb-010` (0.75): Quên mật khẩu Windows / tài kh | ✅ PASS |
| `RET-E01` | `E_ambiguous` | Không vào được | `kb-001, kb-002, kb-003, kb-010, kb-011` | 3 | `kb-032` (0.75): Không submit được đơn xin nghỉ | ✅ PASS |
| `RET-E02` | `E_ambiguous` | Bị lỗi rồi không biết làm sao | `kb-009, kb-015, kb-013` | 3 | `kb-035` (0.75): Dữ liệu bị mất / cần khôi phục | ✅ PASS |
| `RET-F01` | `F_policy_authority` | Quy trình reset mật khẩu khi tài khoản b | `kb-010` | 1 | `kb-010` (0.86): Quên mật khẩu Windows / tài kh | ✅ PASS |
| `RET-F02` | `F_policy_authority` | Quy trình xin cấp quyền truy cập thư mục | `kb-011` | 1 | `kb-011` (0.75): Cấp quyền truy cập thư mục/fil | ✅ PASS |
| `RET-F03` | `F_policy_authority` | Chính sách cài phần mềm mới trên máy côn | `kb-034` | 1 | `kb-034` (0.75): Yêu cầu cài phần mềm mới | ✅ PASS |
| `RET-F04` | `F_policy_authority` | VPN của công ty kết nối như thế nào và y | `kb-001` | 1 | `kb-001` (0.75): Không kết nối được VPN công ty | ✅ PASS |
| `RET-G01` | `G_tenant_isolation` | Hệ thống HIS bệnh viện chạy chậm ảnh hưở | `kb-025` | 1 | `kb-025` (1.00): Hệ thống HIS (Hospital Informa | ✅ PASS |
| `RET-G02` | `G_tenant_isolation` | Phần mềm quản lý dự án bất động sản khôn | `kb-021` | 1 | `kb-021` (1.00): Phần mềm quản lý dự án BĐS khô | ✅ PASS |
| `RET-G03` | `G_tenant_isolation` | Máy MRI không gửi được ảnh lên hệ thống  | `kb-026` | 1 | `kb-026` (1.00): Máy chụp X-quang/MRI không kết | ✅ PASS |
| `RET-G04` | `G_tenant_isolation` | Hệ thống POS showroom xe bị lỗi không in | `kb-024` | 1 | `kb-024` (1.00): Hệ thống POS showroom xe bị lỗ | ✅ PASS |
| `RET-G05` | `G_tenant_isolation` | SAP không đăng nhập được bị khóa tài kho | `kb-019` | 1 | `kb-019` (0.75): SAP không đăng nhập được / ses | ✅ PASS |
| `RET-H01` | `H_no_evidence` | Máy pha cà phê Bluetooth ở pantry không  | `None` | Miss | `kb-033` (0.75): Teams/Zoom không hoạt động khi | ✅ PASS |
| `RET-H02` | `H_no_evidence` | Chính sách nghỉ phép bao nhiêu ngày một  | `kb-032` | 1 | `kb-032` (0.75): Không submit được đơn xin nghỉ | ✅ PASS |
| `RET-H03` | `H_no_evidence` | Giá cổ phiếu công ty tuần trước là bao n | `None` | Miss | `kb-035` (0.75): Dữ liệu bị mất / cần khôi phục | ✅ PASS |
| `RET-I01` | `I_hard_negative` | Mật khẩu VPN khác với mật khẩu email của | `kb-001` | 1 | `kb-001` (0.75): Không kết nối được VPN công ty | ✅ PASS |
| `RET-I02` | `I_hard_negative` | Xin cấp quyền truy cập thư mục file serv | `kb-011` | 1 | `kb-011` (0.78): Cấp quyền truy cập thư mục/fil | ✅ PASS |
| `RET-I03` | `I_hard_negative` | Máy in không in được qua mạng văn phòng | `kb-014` | 1 | `kb-014` (0.75): Máy in không in được / in lỗi | ✅ PASS |
| `RET-I04` | `I_hard_negative` | Outlook báo lỗi authentication khi mở lê | `kb-004` | 1 | `kb-004` (0.75): Outlook không đồng bộ email /  | ✅ PASS |
| `RET-I05` | `I_hard_negative` | Server sản xuất không phản hồi hệ thống  | `kb-028` | 1 | `kb-028` (0.78): Server production bị down | ✅ PASS |
| `RET-I06` | `I_hard_negative` | Máy tính bị nhiễm malware cần ngắt mạng  | `kb-016` | 1 | `kb-016` (1.00): Nghi ngờ máy tính bị nhiễm vir | ✅ PASS |
