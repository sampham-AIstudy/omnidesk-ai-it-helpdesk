# RAG Retrieval Evaluation

- Collection: `helpdesk_kb_multilingual_v1`
- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Documents: 432
- Cases: 12
- Hit@1: 25.0%
- Hit@5: 100.0%
- Recall@5: 100.0%
- MRR: 0.533
- Source relevance: 53.3%
- Noise rate: 46.7%
- Duplicate source rate: 0.0%

| Query | Expected | Rank | Relevance | Noise | Duplicates |
|---|---|---:|---:|---:|---:|
| Máy tính không kết nối được Wi-Fi và báo không có Internet | Khắc phục sự cố Wi-Fi trên Windows | 3 | 40% | 60% | 0% |
| Tôi cần cấu hình kết nối VPN trên Windows để làm việc từ xa | Kết nối VPN trên Windows | 3 | 40% | 60% | 0% |
| Outlook không gửi hoặc nhận được email | Sự cố gửi và nhận email trong Outlook | 3 | 20% | 80% | 0% |
| OneDrive bị kẹt đồng bộ file và hiển thị biểu tượng lỗi | Khắc phục sự cố đồng bộ OneDrive | 5 | 20% | 80% | 0% |
| Máy in Windows đang offline và lệnh in bị kẹt trong queue | Khắc phục lỗi máy in trên Windows | 2 | 60% | 40% | 0% |
| Laptop Windows liên tục màn hình xanh và hiện stop code | Khắc phục lỗi màn hình xanh Windows | 2 | 60% | 40% | 0% |
| Windows Update báo lỗi 0x800f0922 | Khắc phục sự cố Windows Update | 5 | 20% | 80% | 0% |
| Camera Microsoft Teams không hoạt động trong cuộc họp | Camera không hoạt động trong Microsoft Teams | 2 | 60% | 40% | 0% |
| Tôi không tìm thấy khóa khôi phục BitLocker | Tìm khóa khôi phục BitLocker | 1 | 40% | 60% | 0% |
| Người dùng không thể tự đặt lại mật khẩu Microsoft Entra SSPR | Xử lý lỗi tự đặt lại mật khẩu Microsoft Entra | 1 | 100% | 0% | 0% |
| Tài khoản email Microsoft 365 có dấu hiệu bị xâm nhập | Ứng phó tài khoản email Microsoft 365 bị xâm nhập | 1 | 100% | 0% | 0% |
| Thiết bị nghi nhiễm malware cần cô lập khỏi mạng bằng Defender | Cô lập thiết bị bị xâm nhập bằng Microsoft Defender | 2 | 80% | 20% | 0% |
