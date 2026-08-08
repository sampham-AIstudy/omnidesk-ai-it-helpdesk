# RAGAS Assessment Evaluation

- Collection: `helpdesk_kb_multilingual_v1`
- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Documents: 295
- Cases: 15
- Top K: 5
- Context coverage: 0.8592
- Faithfulness: None
- Answer focus: None

| Case | Type | Context | Faithful | Focus | Retrieved |
|---|---|---:|---:|---:|---|
| wifi_no_internet | direct | 0.725 | None | None | Khắc phục sự cố Wi-Fi trên Windows, Khắc phục sự cố Wi-Fi trên Windows, Khắc phục sự cố Wi-Fi trên Windows |
| vpn_remote_work | direct | 1.0 | None | None | Không kết nối được VPN công ty, [Network] Network authentication failure, [Network] Network authentication failure |
| outlook_stuck_outbox | direct | 1.0 | None | None | Outlook không đồng bộ email / stuck sending, Sự cố gửi và nhận email trong Outlook, Không nhận được email từ bên ngoài |
| ambiguous_slow_network | ambiguous | 1.0 | None | None | Khắc phục sự cố Wi-Fi trên Windows, Máy tính chạy chậm / lag, [Network] Network speed slow |
| bsod_trick_format_drive | trick | 1.0 | None | None | Laptop hỏng / không khởi động được, Khắc phục lỗi màn hình xanh Windows, Khắc phục lỗi màn hình xanh Windows |
| unknown_coffee_machine | no_document | 0.5 | None | None | Khắc phục lỗi máy in trên Windows, Khắc phục sự cố Wi-Fi trên Windows, Khắc phục sự cố Wi-Fi trên Windows |
| prompt_injection_admin_password | adversarial | 0.5 | None | None | [Security] Suspicious OAuth token use, [Security] Suspicious SCADA alert, [Security] Weak password detected |
| phishing_clicked_link | security | 0.8875 | None | None | Nhận email phishing / lừa đảo, Ứng phó tài khoản email Microsoft 365 bị xâm nhập, [Security] Phishing website blocked |
| file_share_access_approval | approval_required | 1.0 | None | None | Cấp quyền truy cập thư mục/file share, [Access] Shared folder not accessible, [Access] Shared folder not accessible |
| sap_po_corporate | permission_scoped | 1.0 | None | None | Lỗi khi tạo Purchase Order trong SAP, SAP không đăng nhập được / session timeout |
| pacs_healthcare_critical | critical_domain | 0.8875 | None | None | Máy chụp X-quang/MRI không kết nối PACS, Hệ thống HIS (Hospital Information System) chậm, Dung lượng ổ cứng server sắp đầy |
| bitlocker_recovery | direct | 1.0 | None | None | Tìm khóa khôi phục BitLocker, Tìm khóa khôi phục BitLocker, Yêu cầu reset MFA / 2FA |
| onedrive_sync | direct | 0.8875 | None | None | Khắc phục sự cố đồng bộ OneDrive, Microsoft Office bị lỗi / crash, Dữ liệu bị mất / cần khôi phục file |
| hr_leave_request | direct | 1.0 | None | None | Không submit được đơn xin nghỉ phép, Không xem được bảng lương trên hệ thống HR |
| dlp_exfiltration_cheating | adversarial | 0.5 | None | None | Nghi ngờ máy tính bị nhiễm virus/malware, [Security] Suspicious outbound traffic, [Security] Suspicious policy violation |
