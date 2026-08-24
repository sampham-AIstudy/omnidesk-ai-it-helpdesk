'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  Send,
  ShieldCheck,
} from 'lucide-react';
import api from '@/lib/api';
import { formatServiceSla, SERVICE_CATEGORY_META, type ServiceCatalogItem } from '@/lib/serviceCatalog';

type FieldType = 'text' | 'textarea' | 'select' | 'date';

interface RequestField {
  id: string;
  label: string;
  type: FieldType;
  required?: boolean;
  placeholder?: string;
  hint?: string;
  options?: string[];
  wide?: boolean;
}

interface ServiceRequestConfig {
  categoryLabel: string;
  ownerTeam: string;
  eta: string;
  intro: string;
  preparation: string[];
  fields: RequestField[];
}

const WITH_JUSTIFICATION: RequestField = {
  id: 'justification',
  label: 'Mục đích công việc',
  type: 'textarea',
  required: true,
  wide: true,
  placeholder: 'Nêu công việc cần thực hiện, phạm vi sử dụng và thời hạn mong muốn…',
  hint: 'Thông tin này giúp đội IT xác định mức ưu tiên và quyền phù hợp.',
};

const SERVICE_CONFIGS: Record<string, ServiceRequestConfig> = {
  'Xin laptop mới': {
    categoryLabel: 'Hardware', ownerTeam: 'Workplace IT', eta: '2–4 ngày làm việc',
    intro: 'Cung cấp thiết bị đã được chuẩn hóa, cài đặt và bàn giao theo quy định tài sản CNTT.',
    preparation: ['Mã nhân viên hoặc người nhận thiết bị', 'Ngày cần nhận máy', 'Phần mềm hoặc cấu hình đặc thù'],
    fields: [
      { id: 'recipient', label: 'Người nhận thiết bị', type: 'text', required: true, placeholder: 'Họ tên / mã nhân viên' },
      { id: 'neededBy', label: 'Ngày cần thiết bị', type: 'date', required: true },
      { id: 'deviceProfile', label: 'Cấu hình sử dụng', type: 'select', required: true, options: ['Văn phòng tiêu chuẩn', 'Lập trình / kỹ thuật', 'Thiết kế / đồ họa', 'Quản lý / di chuyển nhiều'] },
      { id: 'software', label: 'Phần mềm cần cài sẵn', type: 'text', placeholder: 'Ví dụ: VS Code, Adobe, SAP GUI' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin máy in': {
    categoryLabel: 'Hardware', ownerTeam: 'Workplace IT', eta: '2–3 ngày làm việc',
    intro: 'Đề nghị cấp mới hoặc kết nối máy in dùng chung cho khu vực làm việc.',
    preparation: ['Vị trí đặt máy / tầng', 'Số lượng người dự kiến sử dụng', 'Loại tài liệu thường in'],
    fields: [
      { id: 'location', label: 'Vị trí sử dụng', type: 'text', required: true, placeholder: 'Tòa nhà, tầng, khu vực' },
      { id: 'printerType', label: 'Nhu cầu in ấn', type: 'select', required: true, options: ['Đen trắng', 'Màu', 'Đa chức năng (in / scan / copy)', 'In nhãn / khổ đặc biệt'] },
      { id: 'users', label: 'Số người dùng dự kiến', type: 'text', required: true, placeholder: 'Ví dụ: 12 người' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin thiết bị ngoại vi': {
    categoryLabel: 'Hardware', ownerTeam: 'Workplace IT', eta: '1–2 ngày làm việc',
    intro: 'Cấp phụ kiện và thiết bị hỗ trợ công việc theo tồn kho và tiêu chuẩn vị trí làm việc.',
    preparation: ['Thiết bị đang sử dụng', 'Loại phụ kiện cần cấp', 'Vị trí nhận thiết bị'],
    fields: [
      { id: 'equipment', label: 'Thiết bị cần cấp', type: 'select', required: true, options: ['Màn hình', 'Headset', 'Webcam', 'Chuột / bàn phím', 'Adapter / dock', 'Khác'] },
      { id: 'device', label: 'Máy tính đang sử dụng', type: 'text', required: true, placeholder: 'Tên máy hoặc mã tài sản' },
      { id: 'location', label: 'Vị trí nhận thiết bị', type: 'text', required: true, placeholder: 'Văn phòng, tầng, khu vực' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin quyền VPN': {
    categoryLabel: 'Access', ownerTeam: 'Network & Security', eta: 'Trong 1 ngày làm việc',
    intro: 'Cấp kết nối VPN an toàn theo nguyên tắc quyền tối thiểu và yêu cầu MFA.',
    preparation: ['Tài khoản cần cấp quyền', 'Hệ thống / mạng nội bộ cần truy cập', 'Thời hạn truy cập nếu là tạm thời'],
    fields: [
      { id: 'account', label: 'Tài khoản cần cấp VPN', type: 'text', required: true, placeholder: 'Email công ty' },
      { id: 'accessScope', label: 'Phạm vi cần truy cập', type: 'select', required: true, options: ['Mạng nội bộ tiêu chuẩn', 'Hệ thống dự án', 'Máy chủ quản trị', 'Theo danh sách hệ thống đính kèm'] },
      { id: 'accessUntil', label: 'Ngày hết hạn (nếu tạm thời)', type: 'date' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin quyền Git repo': {
    categoryLabel: 'Access', ownerTeam: 'Platform Engineering', eta: 'Trong 1 ngày làm việc',
    intro: 'Cấp quyền repository theo vai trò dự án và chính sách bảo vệ mã nguồn.',
    preparation: ['Tài khoản Git hiện có', 'URL hoặc tên repository', 'Owner dự án xác nhận quyền'],
    fields: [
      { id: 'gitAccount', label: 'Tài khoản Git', type: 'text', required: true, placeholder: 'Email / username công ty' },
      { id: 'repository', label: 'Repository cần truy cập', type: 'text', required: true, placeholder: 'Ví dụ: org/project-api' },
      { id: 'permission', label: 'Mức quyền', type: 'select', required: true, options: ['Read', 'Triage', 'Write', 'Maintain', 'Admin (cần phê duyệt bổ sung)'] },
      { id: 'projectOwner', label: 'Project owner phê duyệt', type: 'text', required: true, placeholder: 'Họ tên / email' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin DB access': {
    categoryLabel: 'Access', ownerTeam: 'Data Platform', eta: '1–2 ngày làm việc',
    intro: 'Cấp quyền cơ sở dữ liệu có kiểm soát, ưu tiên quyền đọc và thời hạn rõ ràng.',
    preparation: ['Tên database và môi trường', 'Quyền tối thiểu cần thiết', 'Owner dữ liệu phê duyệt'],
    fields: [
      { id: 'database', label: 'Database / cluster', type: 'text', required: true, placeholder: 'Ví dụ: customer-db' },
      { id: 'dbEnvironment', label: 'Môi trường', type: 'select', required: true, options: ['Development', 'Test / UAT', 'Staging', 'Production'] },
      { id: 'dbPermission', label: 'Quyền cần cấp', type: 'select', required: true, options: ['Read-only', 'Read / Write', 'Schema migration', 'Admin (cần phê duyệt bổ sung)'] },
      { id: 'dataOwner', label: 'Data owner phê duyệt', type: 'text', required: true, placeholder: 'Họ tên / email' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin Microsoft 365 license': {
    categoryLabel: 'Software', ownerTeam: 'Cloud Productivity', eta: 'Trong 1 ngày làm việc',
    intro: 'Phân bổ license Microsoft 365 từ pool hiện có theo vai trò công việc.',
    preparation: ['Tài khoản người dùng', 'Gói license hoặc tính năng cần dùng', 'Ngày cần kích hoạt'],
    fields: [
      { id: 'account', label: 'Tài khoản cần cấp license', type: 'text', required: true, placeholder: 'Email công ty' },
      { id: 'licensePlan', label: 'Gói license', type: 'select', required: true, options: ['Microsoft 365 Business Standard', 'Microsoft 365 E3', 'Microsoft 365 E5', 'Chưa rõ, cần IT tư vấn'] },
      { id: 'neededBy', label: 'Ngày cần kích hoạt', type: 'date', required: true },
      WITH_JUSTIFICATION,
    ],
  },
  'Yêu cầu cài đặt phần mềm được phê duyệt': {
    categoryLabel: 'Software', ownerTeam: 'Workplace IT', eta: 'Trong 1 ngày làm việc',
    intro: 'Cài đặt phần mềm đã có license hoặc thuộc danh mục ứng dụng được công ty cho phép sử dụng.',
    preparation: ['Tên phần mềm và phiên bản nếu biết', 'Thiết bị cần cài', 'License hoặc quản lý xác nhận nếu phần mềm có phí'],
    fields: [
      { id: 'softwareName', label: 'Phần mềm cần cài', type: 'text', required: true, placeholder: 'Ví dụ: Zoom, Adobe Acrobat, Notepad++' },
      { id: 'device', label: 'Tên máy / mã tài sản', type: 'text', required: true, placeholder: 'Ví dụ: LAP-HN-0241' },
      { id: 'licenseSource', label: 'Tình trạng license', type: 'select', required: true, options: ['Đã có license cá nhân', 'Dùng license công ty hiện có', 'Phần mềm miễn phí / open source', 'Cần IT kiểm tra'] },
      { id: 'approver', label: 'Quản lý xác nhận (nếu có phí)', type: 'text', placeholder: 'Họ tên / email' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin antivirus': {
    categoryLabel: 'Software', ownerTeam: 'Endpoint Security', eta: 'Trong 1 ngày làm việc',
    intro: 'Bổ sung bảo vệ endpoint cho thiết bị được công ty phê duyệt sử dụng.',
    preparation: ['Tên hoặc mã tài sản thiết bị', 'Hệ điều hành', 'Vị trí người dùng nếu làm việc từ xa'],
    fields: [
      { id: 'device', label: 'Tên máy / mã tài sản', type: 'text', required: true, placeholder: 'Ví dụ: LAP-HN-0241' },
      { id: 'operatingSystem', label: 'Hệ điều hành', type: 'select', required: true, options: ['Windows 11', 'macOS', 'Linux', 'Khác'] },
      { id: 'deviceOwner', label: 'Người đang sử dụng máy', type: 'text', required: true, placeholder: 'Họ tên / email' },
      WITH_JUSTIFICATION,
    ],
  },
  'Mở khóa tài khoản': {
    categoryLabel: 'Accounts', ownerTeam: 'Identity & Access', eta: 'Trong 30 phút giờ hành chính',
    intro: 'Hỗ trợ khi bạn không thể tự mở khóa tài khoản hoặc self-service password reset không thành công.',
    preparation: ['Username hoặc email công ty', 'Kênh liên hệ để xác thực', 'Dịch vụ không truy cập được'],
    fields: [
      { id: 'account', label: 'Tài khoản cần hỗ trợ', type: 'text', required: true, placeholder: 'Username hoặc email công ty' },
      { id: 'contact', label: 'Kênh liên hệ để xác thực', type: 'text', required: true, placeholder: 'Số điện thoại công ty hoặc email thay thế' },
      { id: 'affectedService', label: 'Dịch vụ không truy cập được', type: 'select', required: true, options: ['Windows / laptop', 'Microsoft 365', 'VPN', 'Ứng dụng nội bộ', 'Khác'] },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin email alias': {
    categoryLabel: 'Accounts', ownerTeam: 'Cloud Productivity', eta: 'Trong 1 ngày làm việc',
    intro: 'Tạo địa chỉ email phụ hoặc mailbox dùng chung theo quy tắc đặt tên của công ty.',
    preparation: ['Tài khoản nhận thư chính', 'Email alias mong muốn', 'Mục đích sử dụng và owner'],
    fields: [
      { id: 'primaryEmail', label: 'Email nhận thư chính', type: 'text', required: true, placeholder: 'name@company.com' },
      { id: 'alias', label: 'Email alias đề xuất', type: 'text', required: true, placeholder: 'Ví dụ: sales-hn@company.com' },
      { id: 'aliasType', label: 'Loại mailbox', type: 'select', required: true, options: ['Alias cá nhân', 'Mailbox dùng chung', 'Nhóm phân phối'] },
      { id: 'owner', label: 'Owner của địa chỉ email', type: 'text', required: true, placeholder: 'Họ tên / phòng ban' },
      WITH_JUSTIFICATION,
    ],
  },
  'Cập nhật tên hiển thị / email': {
    categoryLabel: 'Accounts', ownerTeam: 'Identity & Access', eta: 'Trong 1 ngày làm việc',
    intro: 'Cập nhật tên hiển thị hoặc địa chỉ email theo thông tin đã được HR xác nhận. Không dùng form này để tạo nhân viên mới.',
    preparation: ['Tài khoản hiện tại', 'Thông tin cần thay đổi', 'Mã hoặc xác nhận thay đổi từ HR'],
    fields: [
      { id: 'account', label: 'Tài khoản hiện tại', type: 'text', required: true, placeholder: 'Email công ty hiện tại' },
      { id: 'changeType', label: 'Thông tin cần cập nhật', type: 'select', required: true, options: ['Tên hiển thị', 'Họ tên pháp lý', 'Email sau đổi tên', 'Khác'] },
      { id: 'newValue', label: 'Giá trị mới', type: 'text', required: true, placeholder: 'Thông tin đã được HR xác nhận' },
      { id: 'hrReference', label: 'Mã / xác nhận từ HR', type: 'text', required: true, placeholder: 'Ví dụ: HR-CHG-0124' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin IP tĩnh': {
    categoryLabel: 'Network', ownerTeam: 'Network Operations', eta: '1–2 ngày làm việc',
    intro: 'Đăng ký IP tĩnh cho thiết bị hoặc dịch vụ theo quy hoạch dải địa chỉ mạng.',
    preparation: ['MAC address hoặc tên thiết bị', 'Vị trí / VLAN sử dụng', 'Lý do cần IP cố định'],
    fields: [
      { id: 'device', label: 'Tên thiết bị', type: 'text', required: true, placeholder: 'Hostname / mã tài sản' },
      { id: 'macAddress', label: 'MAC address', type: 'text', required: true, placeholder: 'Ví dụ: 00:1A:2B:3C:4D:5E' },
      { id: 'networkLocation', label: 'Vị trí / VLAN', type: 'text', required: true, placeholder: 'Tòa nhà, tầng, mạng dự kiến' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin truy cập mạng nội bộ': {
    categoryLabel: 'Network', ownerTeam: 'Network & Security', eta: 'Trong 1 ngày làm việc',
    intro: 'Mở quyền truy cập mạng nội bộ hoặc phân đoạn mạng theo phạm vi công việc.',
    preparation: ['Tài khoản hoặc thiết bị cần truy cập', 'Hệ thống / segment đích', 'Thời hạn nếu là quyền tạm thời'],
    fields: [
      { id: 'requestorAccount', label: 'Tài khoản / thiết bị cần truy cập', type: 'text', required: true, placeholder: 'Email, hostname hoặc mã tài sản' },
      { id: 'destination', label: 'Mạng hoặc hệ thống đích', type: 'text', required: true, placeholder: 'Ví dụ: 10.20.0.0/16, file server' },
      { id: 'accessUntil', label: 'Ngày hết hạn (nếu tạm thời)', type: 'date' },
      WITH_JUSTIFICATION,
    ],
  },
  'Đăng ký Wi-Fi cho thiết bị mới': {
    categoryLabel: 'Network', ownerTeam: 'Network Operations', eta: 'Trong 4 giờ làm việc',
    intro: 'Đăng ký thiết bị công ty mới vào mạng Wi-Fi nội bộ theo chính sách endpoint.',
    preparation: ['Tên hoặc mã tài sản thiết bị', 'MAC address Wi-Fi', 'Vị trí sử dụng'],
    fields: [
      { id: 'device', label: 'Tên thiết bị / mã tài sản', type: 'text', required: true, placeholder: 'Ví dụ: LAP-HN-0241' },
      { id: 'macAddress', label: 'Wi-Fi MAC address', type: 'text', required: true, placeholder: 'Ví dụ: 00:1A:2B:3C:4D:5E' },
      { id: 'location', label: 'Vị trí sử dụng', type: 'text', required: true, placeholder: 'Văn phòng, tầng, khu vực' },
      WITH_JUSTIFICATION,
    ],
  },
  'Đăng ký mượn thiết bị tạm thời': {
    categoryLabel: 'Workplace support', ownerTeam: 'Workplace IT', eta: 'Trong 1 ngày làm việc',
    intro: 'Đăng ký mượn thiết bị theo tồn kho cho công tác, thay thế tạm thời hoặc sự kiện ngắn hạn.',
    preparation: ['Thiết bị muốn mượn', 'Ngày nhận và hoàn trả', 'Vị trí nhận thiết bị'],
    fields: [
      { id: 'equipment', label: 'Thiết bị cần mượn', type: 'select', required: true, options: ['Laptop tạm thời', 'Màn hình', 'Headset', 'Webcam', 'Thiết bị trình chiếu'] },
      { id: 'pickupDate', label: 'Ngày nhận thiết bị', type: 'date', required: true },
      { id: 'returnDate', label: 'Ngày hoàn trả dự kiến', type: 'date', required: true },
      { id: 'location', label: 'Vị trí nhận thiết bị', type: 'text', required: true, placeholder: 'Văn phòng / chi nhánh' },
      WITH_JUSTIFICATION,
    ],
  },
  'Xin chuyển máy / bàn làm việc': {
    categoryLabel: 'Workplace support', ownerTeam: 'Workplace IT', eta: '1–2 ngày làm việc',
    intro: 'Điều phối di chuyển thiết bị và hỗ trợ kết nối lại tại vị trí làm việc mới.',
    preparation: ['Người dùng và thiết bị cần chuyển', 'Vị trí hiện tại / vị trí mới', 'Ngày dự kiến di chuyển'],
    fields: [
      { id: 'employee', label: 'Người dùng / bộ phận', type: 'text', required: true, placeholder: 'Họ tên hoặc phòng ban' },
      { id: 'currentLocation', label: 'Vị trí hiện tại', type: 'text', required: true, placeholder: 'Tòa nhà, tầng, bàn' },
      { id: 'newLocation', label: 'Vị trí mới', type: 'text', required: true, placeholder: 'Tòa nhà, tầng, bàn' },
      { id: 'moveDate', label: 'Ngày dự kiến chuyển', type: 'date', required: true },
      WITH_JUSTIFICATION,
    ],
  },
  'Yêu cầu hỗ trợ thiết bị phòng họp': {
    categoryLabel: 'Workplace support', ownerTeam: 'Workplace IT', eta: 'Trong 4 giờ làm việc',
    intro: 'Chuẩn bị hoặc kiểm tra thiết bị họp trực tuyến cho cuộc họp nội bộ, đào tạo hoặc trình bày tại văn phòng.',
    preparation: ['Tên phòng họp', 'Thời gian diễn ra', 'Thiết bị hoặc hình thức họp cần hỗ trợ'],
    fields: [
      { id: 'room', label: 'Phòng họp / vị trí', type: 'text', required: true, placeholder: 'Ví dụ: Phòng họp A, tầng 8' },
      { id: 'meetingDate', label: 'Ngày cần hỗ trợ', type: 'date', required: true },
      { id: 'meetingType', label: 'Nhu cầu hỗ trợ', type: 'select', required: true, options: ['Trình chiếu', 'Họp trực tuyến', 'Camera / microphone', 'Kiểm tra toàn bộ phòng họp'] },
      { id: 'timeWindow', label: 'Khung giờ', type: 'text', required: true, placeholder: 'Ví dụ: 09:00 – 11:00' },
      WITH_JUSTIFICATION,
    ],
  },
};

const CATEGORY_DEFAULTS: Record<string, ServiceRequestConfig> = {
  hardware: { categoryLabel: 'Hardware', ownerTeam: 'Workplace IT', eta: '1–3 ngày làm việc', intro: 'Hãy cung cấp thông tin cần thiết để đội Workplace IT chuẩn bị thiết bị hoặc môi trường phù hợp.', preparation: ['Người nhận', 'Thời hạn cần dùng', 'Yêu cầu cấu hình'], fields: [{ id: 'recipient', label: 'Người cần sử dụng', type: 'text', required: true, placeholder: 'Họ tên / mã nhân viên' }, WITH_JUSTIFICATION] },
  access: { categoryLabel: 'Access', ownerTeam: 'Identity & Access', eta: 'Trong 1 ngày làm việc', intro: 'Các quyền truy cập được cấp theo nguyên tắc quyền tối thiểu và có thể cần owner phê duyệt.', preparation: ['Tài khoản cần cấp', 'Hệ thống đích', 'Owner phê duyệt'], fields: [{ id: 'account', label: 'Tài khoản cần cấp', type: 'text', required: true, placeholder: 'Email công ty' }, { id: 'scope', label: 'Phạm vi truy cập', type: 'text', required: true, placeholder: 'Hệ thống / repository / database' }, WITH_JUSTIFICATION] },
  software: { categoryLabel: 'Software', ownerTeam: 'IT Applications', eta: '1–2 ngày làm việc', intro: 'Cấp phần mềm theo license và vai trò công việc đã được phê duyệt.', preparation: ['Tài khoản người dùng', 'Tên phần mềm', 'Ngày cần sử dụng'], fields: [{ id: 'account', label: 'Tài khoản cần cấp', type: 'text', required: true, placeholder: 'Email công ty' }, { id: 'software', label: 'Phần mềm cần dùng', type: 'text', required: true, placeholder: 'Tên phần mềm / gói license' }, WITH_JUSTIFICATION] },
  accounts: { categoryLabel: 'Accounts', ownerTeam: 'Identity & Access', eta: 'Trong 1 ngày làm việc', intro: 'Đội Identity & Access sẽ xử lý yêu cầu tài khoản sau khi xác thực thông tin người dùng.', preparation: ['Tài khoản liên quan', 'Thông tin xác thực cần thiết', 'Mục đích yêu cầu'], fields: [{ id: 'account', label: 'Tài khoản liên quan', type: 'text', required: true, placeholder: 'Email / username công ty' }, WITH_JUSTIFICATION] },
  network: { categoryLabel: 'Network', ownerTeam: 'Network Operations', eta: '1–2 ngày làm việc', intro: 'Yêu cầu mạng được kiểm tra theo chính sách phân vùng và an toàn thông tin.', preparation: ['Thiết bị hoặc tài khoản', 'Nguồn và đích truy cập', 'Thời hạn nếu tạm thời'], fields: [{ id: 'target', label: 'Thiết bị / hệ thống liên quan', type: 'text', required: true, placeholder: 'Hostname, IP hoặc email' }, WITH_JUSTIFICATION] },
  onboarding: { categoryLabel: 'Workplace support', ownerTeam: 'Workplace IT', eta: 'Trong 1 ngày làm việc', intro: 'Hãy cung cấp thông tin để Workplace IT chuẩn bị hoặc hỗ trợ thiết bị tại nơi làm việc.', preparation: ['Thiết bị hoặc phòng họp liên quan', 'Thời hạn cần hỗ trợ', 'Vị trí thực hiện'], fields: [{ id: 'subject', label: 'Thiết bị / vị trí liên quan', type: 'text', required: true, placeholder: 'Mã tài sản, phòng họp hoặc vị trí làm việc' }, { id: 'neededBy', label: 'Ngày cần hỗ trợ', type: 'date', required: true }, WITH_JUSTIFICATION] },
};

const FALLBACK_CONFIG: ServiceRequestConfig = {
  categoryLabel: 'Service request', ownerTeam: 'IT Service Desk', eta: '1–2 ngày làm việc',
  intro: 'Cung cấp thông tin đầy đủ để đội IT chuyển yêu cầu đến đúng nhóm xử lý.',
  preparation: ['Người cần hỗ trợ', 'Phạm vi yêu cầu', 'Thời hạn mong muốn'],
  fields: [{ id: 'requestDetails', label: 'Thông tin yêu cầu', type: 'textarea', required: true, wide: true, placeholder: 'Mô tả nhu cầu và thông tin liên quan…' }, WITH_JUSTIFICATION],
};

function Field({ field, value, onChange, error }: { field: RequestField; value: string; onChange: (value: string) => void; error?: string }) {
  const inputClassName = `input-field ${error ? 'border-red-400' : ''}`;
  return (
    <div className={`form-field ${field.wide ? 'md:col-span-2' : ''}`}>
      <label htmlFor={field.id}>{field.label}{field.required && <span className="text-red-600"> *</span>}</label>
      {field.type === 'textarea' ? (
        <textarea id={field.id} rows={field.id === 'justification' ? 4 : 3} className={inputClassName} value={value} onChange={(event) => onChange(event.target.value)} placeholder={field.placeholder} aria-invalid={Boolean(error)} />
      ) : field.type === 'select' ? (
        <select id={field.id} className={inputClassName} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={Boolean(error)}>
          <option value="">Chọn một phương án</option>
          {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : (
        <input id={field.id} type={field.type} className={inputClassName} value={value} onChange={(event) => onChange(event.target.value)} placeholder={field.placeholder} aria-invalid={Boolean(error)} />
      )}
      {error ? <span className="field-error">{error}</span> : field.hint ? <span className="field-hint">{field.hint}</span> : null}
    </div>
  );
}

function ServiceRequestForm() {
  const params = useSearchParams();
  const router = useRouter();
  const service = params.get('item') || 'Yêu cầu dịch vụ IT';
  const category = params.get('category') || 'other';
  const baseConfig = useMemo(() => SERVICE_CONFIGS[service] || CATEGORY_DEFAULTS[category] || FALLBACK_CONFIG, [category, service]);
  const catalogQuery = useQuery({
    queryKey: ['service-catalog'],
    queryFn: async () => (await api.get<{ items: ServiceCatalogItem[] }>('/service-requests/catalog')).data.items,
    staleTime: 60_000,
  });
  const catalogItem = catalogQuery.data?.find((item) => item.service_name === service);
  const config = useMemo(() => catalogItem ? {
    ...baseConfig,
    categoryLabel: SERVICE_CATEGORY_META[catalogItem.category]?.label ?? baseConfig.categoryLabel,
    ownerTeam: catalogItem.fulfillment_group,
    eta: formatServiceSla(catalogItem.sla_hours),
  } : baseConfig, [baseConfig, catalogItem]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState<{ request_number: string; status: string } | null>(null);

  const updateValue = (id: string, value: string) => {
    setValues((current) => ({ ...current, [id]: value }));
    if (errors[id]) setErrors((current) => ({ ...current, [id]: '' }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    for (const field of config.fields) {
      if (field.required && !values[field.id]?.trim()) nextErrors[field.id] = 'Trường này là bắt buộc.';
    }
    if ((values.justification?.trim().length || 0) > 0 && values.justification.trim().length < 10) {
      nextErrors.justification = 'Vui lòng nêu mục đích công việc ít nhất 10 ký tự.';
    }
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      toast.error('Vui lòng hoàn tất các trường bắt buộc.');
      return;
    }

    setReviewing(true);
  };

  const confirmSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await api.post('/service-requests', {
        service_name: service,
        category,
        form_data: values,
      });
      setSubmittedRequest(result.data);
      toast.success('Đã gửi Service Request');
    } catch {
      toast.error('Không thể tạo yêu cầu. Vui lòng thử lại.');
    } finally {
      setSubmitting(false);
    }
  };

  const submittedFields = config.fields.filter((field) => values[field.id]?.trim());

  if (submittedRequest) {
    const pendingApproval = submittedRequest.status === 'pending_approval';
    return <main className="mx-auto max-w-2xl py-10"><section className="overflow-hidden rounded-2xl border border-emerald-200 bg-white shadow-sm"><div className="border-b border-emerald-100 bg-emerald-50 px-7 py-8 text-center"><CheckCircle2 size={40} className="mx-auto text-emerald-600" /><p className="mt-4 text-sm font-semibold text-emerald-800">Request submitted</p><h1 className="mt-1 font-mono text-2xl font-semibold text-slate-950">{submittedRequest.request_number}</h1><p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-600">Yêu cầu <strong>{service}</strong> đã được tách riêng khỏi Incident và chuyển vào quy trình fulfillment.</p></div><div className="p-7"><div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500">Trạng thái hiện tại</p><p className="mt-1 text-sm font-semibold text-slate-900">{pendingApproval ? 'Chờ phê duyệt' : 'Đã gửi đội xử lý'}</p><p className="mt-1 text-xs leading-5 text-slate-600">{pendingApproval ? 'Manager/owner sẽ nhận được yêu cầu phê duyệt trước khi IT tiến hành cấp phát.' : `Đã chuyển đến ${config.ownerTeam}.`}</p></div><div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center"><button type="button" onClick={() => router.push(`/employee/requests/${submittedRequest.request_number}`)} className="btn-primary">Xem yêu cầu</button><Link href="/employee/catalog" className="btn-ghost">Quay lại Service Catalog</Link></div></div></section></main>;
  }

  if (reviewing) {
    return <main className="mx-auto max-w-4xl pb-10"><div className="mb-6 flex items-center gap-2 text-xs font-medium text-slate-500"><Link href="/employee/catalog" className="hover:text-blue-700">Service catalog</Link><ChevronRight size={14} className="text-slate-300" /><span className="text-slate-700">Review request</span></div><section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><header className="border-b border-slate-200 bg-slate-50 px-6 py-6 md:px-8"><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-700">Review · {config.categoryLabel}</p><h1 className="mt-2 text-2xl font-semibold text-slate-950">{service}</h1><p className="mt-2 text-sm text-slate-600">Kiểm tra thông tin trước khi gửi vào workflow Service Request.</p></header><div className="grid lg:grid-cols-[minmax(0,1fr)_260px]"><div className="p-6 md:p-8"><dl className="divide-y divide-slate-100">{submittedFields.map((field) => <div key={field.id} className="grid gap-1 py-4 sm:grid-cols-[180px_1fr]"><dt className="text-xs font-semibold text-slate-500">{field.label}</dt><dd className="whitespace-pre-wrap text-sm leading-6 text-slate-900">{values[field.id]}</dd></div>)}</dl><div className="mt-7 flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between"><button type="button" onClick={() => setReviewing(false)} className="text-sm font-medium text-slate-600 hover:text-slate-900">← Chỉnh sửa thông tin</button><button type="button" onClick={confirmSubmit} className="btn-primary h-10 px-5" disabled={submitting}><Send size={16} /> {submitting ? 'Đang gửi…' : 'Submit request'}</button></div></div><aside className="border-t border-slate-200 bg-slate-50 p-6 lg:border-l lg:border-t-0"><p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500">Request process</p><ol className="mt-5 grid gap-4 text-sm"><li className="font-semibold text-blue-700">1. Submit request</li><li className="text-slate-600">2. Approval theo chính sách</li><li className="text-slate-600">3. {config.ownerTeam} fulfillment</li><li className="text-slate-600">4. Xác nhận và đóng</li></ol><div className="mt-7 border-t border-slate-200 pt-4"><p className="text-xs font-semibold text-slate-800">Dự kiến hoàn tất</p><p className="mt-1 text-sm text-slate-600">{config.eta} sau khi đủ phê duyệt</p></div></aside></div></section></main>;
  }

  return (
    <main className="mx-auto max-w-6xl pb-10">
      <div className="mb-6 flex items-center gap-2 text-xs font-medium text-slate-500">
        <Link href="/employee/catalog" className="inline-flex items-center gap-1 hover:text-blue-700 transition-colors"><ArrowLeft size={14} /> Service catalog</Link>
        <ChevronRight size={14} className="text-slate-300" />
        <span className="text-slate-700">Tạo yêu cầu</span>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-200 bg-slate-50 px-6 py-6 md:px-8">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-700">{config.categoryLabel} · service request</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">{service}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{config.intro}</p>
            </div>
            <div className="shrink-0 rounded-xl border border-blue-100 bg-blue-50 px-3.5 py-3 text-xs text-blue-900">
              <div className="flex items-center gap-2 font-semibold"><Clock3 size={15} className="text-blue-600" /> Dự kiến xử lý</div>
              <p className="mt-1 pl-6 text-blue-700">{config.eta}</p>
            </div>
          </div>
        </header>

        <div className="grid lg:grid-cols-[minmax(0,1fr)_280px]">
          <form onSubmit={submit} className="p-6 md:p-8">
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3">
              <ShieldCheck size={18} className="mt-0.5 shrink-0 text-emerald-700" />
              <p className="text-xs leading-5 text-emerald-900">Chỉ cung cấp thông tin phục vụ yêu cầu. Không nhập mật khẩu, mã OTP, khóa truy cập hoặc dữ liệu nhạy cảm.</p>
            </div>
            <div className="mb-5 flex items-center gap-2">
              <FileText size={17} className="text-blue-700" />
              <div><h2 className="text-base font-semibold text-slate-900">Thông tin cần cung cấp</h2><p className="mt-0.5 text-xs text-slate-500">Các trường có dấu * sẽ được dùng để chuyển đúng nhóm xử lý.</p></div>
            </div>
            <div className="grid gap-x-5 gap-y-5 md:grid-cols-2">
              {config.fields.map((field) => <Field key={field.id} field={field} value={values[field.id] || ''} onChange={(value) => updateValue(field.id, value)} error={errors[field.id]} />)}
            </div>
            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <Link href="/employee/catalog" className="text-center text-sm font-medium text-slate-600 hover:text-slate-900">Hủy và quay lại catalog</Link>
              <button type="submit" className="btn-primary h-10 px-5"><ChevronRight size={16} /> Review request</button>
            </div>
          </form>

          <aside className="border-t border-slate-200 bg-slate-50 p-6 lg:border-l lg:border-t-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Chuẩn bị trước</p>
            <ul className="mt-4 grid gap-3">
              {config.preparation.map((item) => <li key={item} className="flex gap-2.5 text-sm leading-5 text-slate-700"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-600" />{item}</li>)}
            </ul>
            <div className="mt-7 border-t border-slate-200 pt-5">
              <p className="text-xs font-semibold text-slate-800">Nhóm xử lý</p>
              <p className="mt-1 text-sm text-slate-600">{config.ownerTeam}</p>
              <p className="mt-4 text-xs font-semibold text-slate-800">Bạn cần hỗ trợ gấp?</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">Nếu một dịch vụ đang bị gián đoạn, hãy tạo Incident Ticket thay vì Service Request.</p>
              <Link href="/employee/new-ticket" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:text-blue-900">Tạo Incident Ticket <ChevronRight size={13} /></Link>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}

export default function NewServiceRequestPage() {
  return <Suspense fallback={<main className="mx-auto max-w-6xl py-10 text-sm text-slate-500">Đang tải biểu mẫu yêu cầu…</main>}><ServiceRequestForm /></Suspense>;
}
