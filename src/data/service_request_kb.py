"""Canonical Service Request Process Knowledge Base Document (KB-GAP-1).

This document is grounded strictly in the implemented P-236 Service Request lifecycle,
catalog policies, approval workflows, and technician fulfillment architecture.
"""
from __future__ import annotations

SERVICE_REQUEST_KB_ENTRY: dict[str, object] = {
    "id": "kb-036",
    "title": "Quy trình Service Request / Yêu cầu dịch vụ CNTT",
    "content": (
        "1. Service Request là gì?\n"
        "Service Request (Yêu cầu dịch vụ) là quy trình chính thức để nhân viên gửi các đề nghị cấp mới thiết bị, cấp quyền truy cập, cài đặt phần mềm, tạo tài khoản hoặc các dịch vụ CNTT chuẩn hóa từ danh mục Service Catalog nội bộ. Mỗi yêu cầu được cấp mã định danh duy nhất theo định dạng REQ-YYYYMMDD-XXXX (ví dụ REQ-20260816-A1B2).\n\n"
        "2. Khi nào dùng Service Request?\n"
        "Nhân viên sử dụng Service Request khi có nhu cầu được cung cấp tài nguyên, quyền hạn hoặc dịch vụ CNTT mới phục vụ công việc hàng ngày hoặc tiếp nhận nhân sự mới (onboarding). Các nhóm dịch vụ bao gồm:\n"
        "- Hardware: Xin laptop mới, xin máy in, xin thiết bị ngoại vi.\n"
        "- Access: Xin quyền VPN, xin quyền Git repository, xin quyền truy cập Database (DB access).\n"
        "- Software: Xin license Microsoft 365, yêu cầu cài đặt phần mềm được phê duyệt, xin antivirus.\n"
        "- Accounts: Đặt lại mật khẩu, mở khóa tài khoản, xin email alias, cập nhật tên hiển thị / email.\n"
        "- Network: Xin IP tĩnh, xin truy cập mạng nội bộ, đăng ký Wi-Fi cho thiết bị mới.\n"
        "- Onboarding: Đăng ký mượn thiết bị tạm thời, xin chuyển máy / bàn làm việc, yêu cầu hỗ trợ thiết bị phòng họp.\n\n"
        "3. Incident khác Service Request thế nào?\n"
        "- Incident (Sự cố CNTT - mã INC-xxxx): Sử dụng khi một dịch vụ, hệ thống hoặc thiết bị đang hoạt động bình thường bỗng nhiên bị gián đoạn, lỗi hoặc hỏng hóc (ví dụ: máy tính mất mạng, VPN báo lỗi 809, Outlook không gửi được thư, máy in kẹt giấy). Mục tiêu là khắc phục lỗi nhanh nhất để khôi phục công việc.\n"
        "- Service Request (Yêu cầu dịch vụ - mã REQ-xxxx): Sử dụng khi cần cấp mới, thay đổi thông tin, xin quyền hoặc cung cấp dịch vụ CNTT chuẩn theo danh mục có sẵn (không phải do hệ thống bị hỏng).\n\n"
        "4. Quy trình sau khi gửi yêu cầu:\n"
        "- Bước 1: Nhân viên chọn dịch vụ từ Service Catalog và gửi biểu mẫu thông tin.\n"
        "- Bước 2: Hệ thống kiểm tra chính sách phê duyệt (approval policy). Nếu dịch vụ yêu cầu phê duyệt, trạng thái ban đầu là PENDING_APPROVAL. Nếu không cần phê duyệt, trạng thái chuyển thẳng sang SUBMITTED.\n"
        "- Bước 3: Admin xem xét và đưa ra quyết định: phê duyệt chuyển sang SUBMITTED, từ chối chuyển sang REJECTED (kết thúc).\n"
        "- Bước 4: Yêu cầu ở trạng thái SUBMITTED xuất hiện trong hàng đợi của nhóm kỹ thuật viên phụ trách (fulfillment_group). Kỹ thuật viên đủ quyền trong nhóm thực hiện tiếp nhận (takeover), trạng thái chuyển sang ASSIGNED.\n"
        "- Bước 5: Kỹ thuật viên bắt đầu xử lý yêu cầu, trạng thái chuyển sang IN_PROGRESS.\n"
        "- Bước 6: Nếu cần thêm thông tin hoặc người dùng phối hợp, kỹ thuật viên chuyển sang WAITING_FOR_USER. Khi tiếp tục làm việc, trạng thái chuyển lại IN_PROGRESS.\n"
        "- Bước 7: Kỹ thuật viên hoàn tất công việc, trạng thái chuyển sang FULFILLED (hoàn tất thành công).\n\n"
        "5. Khi nào cần phê duyệt?\n"
        "Chính sách phê duyệt được cấu hình máy chủ quản lý (server-owned policy), người dùng không thể tự ý bỏ qua bước duyệt:\n"
        "- Cần Admin phê duyệt: Xin laptop mới, xin máy in, xin thiết bị ngoại vi, xin quyền VPN, xin quyền Git repo, xin DB access, xin Microsoft 365 license, xin email alias, cập nhật tên hiển thị/email (xác thực hồ sơ HR), xin truy cập mạng nội bộ, mượn thiết bị tạm thời.\n"
        "- Không cần phê duyệt (Chuyển thẳng SUBMITTED): Đặt lại mật khẩu, mở khóa tài khoản, xin antivirus, cài đặt phần mềm đã được phê duyệt, xin IP tĩnh, đăng ký Wi-Fi thiết bị mới, chuyển máy/bàn làm việc, hỗ trợ thiết bị phòng họp.\n\n"
        "6. Ai xử lý yêu cầu?\n"
        "Sau khi ở trạng thái SUBMITTED, yêu cầu được phân luồng tự động vào đúng nhóm kỹ thuật viên phụ trách (Fulfillment Group):\n"
        "- Identity & Access: Xử lý mật khẩu, mở khóa tài khoản, cập nhật tên/email.\n"
        "- Workplace IT: Xử lý laptop, máy in, thiết bị ngoại vi, cài đặt phần mềm, thiết bị phòng họp, chuyển bàn làm việc.\n"
        "- Network & Security / Network Operations: Xử lý VPN, mạng nội bộ, IP tĩnh, Wi-Fi thiết bị mới.\n"
        "- Platform Engineering: Xử lý phân quyền Git repository.\n"
        "- Data Platform: Xử lý phân quyền cơ sở dữ liệu (DB access).\n"
        "- Cloud Productivity: Xử lý Microsoft 365 license, email alias.\n"
        "- Endpoint Security: Xử lý phần mềm antivirus.\n"
        "Chỉ kỹ thuật viên có quyền thành viên chính thức trong nhóm phụ trách mới có thể tiếp nhận và xử lý yêu cầu.\n\n"
        "7. Ý nghĩa các trạng thái:\n"
        "- PENDING_APPROVAL: Chờ Admin phê duyệt. Kỹ thuật viên chưa thấy yêu cầu này trong hàng đợi.\n"
        "- SUBMITTED: Đã gửi hợp lệ hoặc đã được duyệt, đang chờ kỹ thuật viên tiếp nhận.\n"
        "- ASSIGNED: Kỹ thuật viên trong nhóm phụ trách đã nhận xử lý yêu cầu.\n"
        "- IN_PROGRESS: Kỹ thuật viên đang trong quá trình thực hiện cấp phát / cấu hình.\n"
        "- WAITING_FOR_USER: Tạm dừng để chờ nhân viên cung cấp thêm thông tin hoặc phối hợp kiểm tra.\n"
        "- FULFILLED: Dịch vụ đã được cung cấp hoàn tất thành công.\n"
        "- REJECTED: Yêu cầu bị Admin từ chối (kèm lý do từ chối cụ thể).\n\n"
        "8. Khi yêu cầu bị từ chối:\n"
        "Nếu bị Admin từ chối, trạng thái chuyển sang REJECTED và không chuyển cho kỹ thuật viên. Nhân viên có thể xem lý do từ chối (rejection_reason) trên màn hình chi tiết yêu cầu để trao đổi lại với Admin hoặc tạo yêu cầu mới.\n\n"
        "9. Khi kỹ thuật viên cần thêm thông tin:\n"
        "Khi trạng thái chuyển sang WAITING_FOR_USER, nhân viên cần bổ sung thông tin được yêu cầu để kỹ thuật viên chuyển lại sang IN_PROGRESS và tiếp tục xử lý.\n\n"
        "10. Khi nào yêu cầu được hoàn tất?\n"
        "Yêu cầu hoàn tất (FULFILLED) khi kỹ thuật viên đã hoàn thành mọi thủ tục cấp phát thiết bị, kích hoạt tài khoản hoặc phân quyền và ghi nhận thời gian hoàn tất.\n\n"
        "11. Ví dụ theo danh mục Service Catalog:\n"
        "- Hardware: Xin laptop mới (cần Admin duyệt, SLA 24h, nhóm Workplace IT).\n"
        "- Access: Xin quyền VPN (cần Admin duyệt, SLA 4h, nhóm Network & Security).\n"
        "- Software: Xin Microsoft 365 license (cần Admin duyệt, SLA 8h, nhóm Cloud Productivity).\n"
        "- Accounts: Đặt lại mật khẩu (không cần duyệt, SLA 1h, nhóm Identity & Access).\n"
        "- Network: Đăng ký Wi-Fi cho thiết bị mới (không cần duyệt, SLA 4h, nhóm Network Operations).\n"
        "- Onboarding: Đăng ký mượn thiết bị tạm thời (cần Admin duyệt, SLA 8h, nhóm Workplace IT)."
    ),
    "solution": (
        "Quy trình xử lý Service Request chuẩn:\n"
        "1. Nhân viên gửi yêu cầu từ Service Catalog.\n"
        "2. Nếu cần duyệt: PENDING_APPROVAL -> Admin duyệt -> SUBMITTED (hoặc REJECTED nếu từ chối).\n"
        "3. Nếu không cần duyệt: Chuyển thẳng sang SUBMITTED.\n"
        "4. Kỹ thuật viên nhóm phụ trách tiếp nhận: SUBMITTED -> ASSIGNED -> IN_PROGRESS -> (WAITING_FOR_USER nếu cần thêm thông tin) -> FULFILLED."
    ),
    "runbook": '{"steps": ["User selects service from catalog and submits form", "System checks approval policy: PENDING_APPROVAL or SUBMITTED", "Admin approves or rejects (REJECTED)", "Technician with matching fulfillment group takes over (ASSIGNED)", "Technician starts work (IN_PROGRESS) or requests info (WAITING_FOR_USER)", "Technician fulfills service (FULFILLED)"]}',
    "category": "service_request",
    "tags": "service request,yêu cầu dịch vụ,quy trình,phê duyệt,pending_approval,submitted,assigned,in_progress,waiting_for_user,fulfilled,rejected,kỹ thuật viên,fulfillment group,catalog,incident khác service request,ai duyệt,khi nào hoàn tất",
    "applicable_to_all": True,
    "source": "internal_curated_kb",
}
