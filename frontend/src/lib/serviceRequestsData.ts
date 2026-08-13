import {
  FileClock,
  UserCheck,
  ShieldCheck,
  PackageOpen,
  Cpu,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export type StatusKey =
  | 'SUBMITTED'
  | 'MANAGER_APPROVAL'
  | 'IT_APPROVAL'
  | 'FULFILLMENT'
  | 'PROVISIONING'
  | 'COMPLETED'
  | 'REJECTED';

export type PriorityKey = 'P0' | 'P1' | 'P2' | 'P3';

export interface TimelineStep {
  key: StatusKey;
  title: string;
  subTitle: string;
  doneAt?: string;
  note?: string;
}

export interface SubTask {
  id: string;
  title: string;
  completed: boolean;
}

export interface FulfillmentItem {
  id: string;
  name: string;
  status: StatusKey;
  assignee?: string;
  updatedAt: string;
  subTasks?: SubTask[];
}

export interface ServiceRequest {
  id: string;
  title: string;
  category: string;
  status: StatusKey;
  priority: PriorityKey;
  createdAt: string;
  requester: string;
  department: string;
  costCenter: string;
  description: string;
  rejectionReason?: string;
  items: FulfillmentItem[];
  timeline: TimelineStep[];
}

export const STATUS_SEQUENCE: StatusKey[] = [
  'SUBMITTED',
  'MANAGER_APPROVAL',
  'IT_APPROVAL',
  'FULFILLMENT',
  'PROVISIONING',
  'COMPLETED',
];

export const STATUS_META: Record<
  StatusKey,
  {
    label: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    color: string;
    borderClass: string;
    bgClass: string;
    textClass: string;
    dotClass: string;
  }
> = {
  SUBMITTED: {
    label: 'Gửi yêu cầu',
    icon: FileClock,
    color: '#22d3ee',
    borderClass: 'border-cyan-200',
    bgClass: 'bg-cyan-50',
    textClass: 'text-cyan-700',
    dotClass: 'bg-cyan-500',
  },
  MANAGER_APPROVAL: {
    label: 'Chờ duyệt QL',
    icon: UserCheck,
    color: '#fbbf24',
    borderClass: 'border-amber-200',
    bgClass: 'bg-amber-50',
    textClass: 'text-amber-700',
    dotClass: 'bg-amber-500',
  },
  IT_APPROVAL: {
    label: 'Chờ duyệt IT',
    icon: ShieldCheck,
    color: '#fb923c',
    borderClass: 'border-orange-200',
    bgClass: 'bg-orange-50',
    textClass: 'text-orange-700',
    dotClass: 'bg-orange-500',
  },
  FULFILLMENT: {
    label: 'Đang fulfillment',
    icon: PackageOpen,
    color: '#60a5fa',
    borderClass: 'border-blue-200',
    bgClass: 'bg-blue-50',
    textClass: 'text-blue-700',
    dotClass: 'bg-blue-500',
  },
  PROVISIONING: {
    label: 'Đang provisioning',
    icon: Cpu,
    color: '#2dd4bf',
    borderClass: 'border-teal-200',
    bgClass: 'bg-teal-50',
    textClass: 'text-teal-700',
    dotClass: 'bg-teal-500',
  },
  COMPLETED: {
    label: 'Hoàn tất',
    icon: CheckCircle2,
    color: '#34d399',
    borderClass: 'border-emerald-200',
    bgClass: 'bg-emerald-50',
    textClass: 'text-emerald-700',
    dotClass: 'bg-emerald-500',
  },
  REJECTED: {
    label: 'Từ chối',
    icon: XCircle,
    color: '#f87171',
    borderClass: 'border-red-200',
    bgClass: 'bg-red-50',
    textClass: 'text-red-700',
    dotClass: 'bg-red-500',
  },
};

export const PRIORITY_META: Record<
  PriorityKey,
  { label: string; classNames: string }
> = {
  P0: { label: 'P0', classNames: 'bg-red-50 border border-red-200 text-red-700 font-mono' },
  P1: { label: 'P1', classNames: 'bg-orange-50 border border-orange-200 text-orange-700 font-mono' },
  P2: { label: 'P2', classNames: 'bg-amber-50 border border-amber-200 text-amber-700 font-mono' },
  P3: { label: 'P3', classNames: 'bg-slate-100 border border-slate-200 text-slate-600 font-mono' },
};

export const MOCK_REQUESTS: ServiceRequest[] = [
  {
    id: 'REQ-2026-00821',
    title: 'Request Microsoft 365 License',
    category: 'Software',
    status: 'MANAGER_APPROVAL',
    priority: 'P0',
    createdAt: '06/08/2026 09:14',
    requester: 'Nguyễn Văn An',
    department: 'Phòng Kế Toán',
    costCenter: 'PRJ-2026-014',
    description:
      'Yêu cầu cấp 2 license Microsoft 365 Business Basic cho team Kế toán để dùng Outlook + Excel Online + OneDrive 1TB mỗi người.',
    items: [
      {
        id: 'FL-2026-0001',
        name: 'M365 Business Basic — License #1',
        status: 'MANAGER_APPROVAL',
        assignee: 'Lê Minh Công',
        updatedAt: '06/08/2026 11:02',
        subTasks: [
          { id: 'st-1', title: 'Tạo user Entra ID', completed: true },
          { id: 'st-2', title: 'Gán license M365', completed: false },
          { id: 'st-3', title: 'Gửi thông báo', completed: false },
        ],
      },
      {
        id: 'FL-2026-0002',
        name: 'M365 Business Basic — License #2',
        status: 'MANAGER_APPROVAL',
        assignee: 'Lê Minh Công',
        updatedAt: '06/08/2026 11:02',
        subTasks: [
          { id: 'st-4', title: 'Tạo user Entra ID', completed: true },
          { id: 'st-5', title: 'Gán license M365', completed: false },
          { id: 'st-6', title: 'Gửi thông báo', completed: false },
        ],
      },
    ],
    timeline: [
      {
        key: 'SUBMITTED',
        title: 'Submitted',
        subTitle: 'Gửi yêu cầu',
        doneAt: '06/08/2026 09:14',
        note: 'Tự động sau khi gửi form trực tuyến.',
      },
      {
        key: 'MANAGER_APPROVAL',
        title: 'Manager Approval',
        subTitle: 'Duyệt Quản lý',
        note: 'Đang chờ phê duyệt của Trưởng phòng — Phạm Thị Dung.',
      },
      {
        key: 'IT_APPROVAL',
        title: 'IT Approval',
        subTitle: 'Duyệt IT',
        note: 'Chờ đánh giá ma trận chi phí của Trưởng phòng IT.',
      },
      {
        key: 'FULFILLMENT',
        title: 'Fulfillment',
        subTitle: 'Chuẩn bị & cấp phát',
        note: 'IT Support kiểm tra kho license khả dụng.',
      },
      {
        key: 'PROVISIONING',
        title: 'Provisioning',
        subTitle: 'Cấu hình hệ thống',
        note: 'Cấu hình tự động qua Entra ID Bot.',
      },
      {
        key: 'COMPLETED',
        title: 'Completed',
        subTitle: 'Hoàn tất',
        note: 'Bàn giao quyền sử dụng cho người yêu cầu.',
      },
    ],
  },
  {
    id: 'REQ-2026-00814',
    title: 'Xin cấp VPN Access cho nhân viên làm từ xa',
    category: 'Access',
    status: 'FULFILLMENT',
    priority: 'P1',
    createdAt: '05/08/2026 14:30',
    requester: 'Nguyễn Văn An',
    department: 'Phòng Kế Toán',
    costCenter: 'ACC-2026-002',
    description: 'Cấp quyền truy cập GlobalProtect VPN cho dự án làm việc xa trụ sở.',
    items: [
      {
        id: 'FL-2026-0005',
        name: 'GlobalProtect VPN Profile & Profile Certificate',
        status: 'FULFILLMENT',
        assignee: 'Lê Minh Công',
        updatedAt: '06/08/2026 08:15',
        subTasks: [
          { id: 'st-10', title: 'Xác minh hồ sơ nhân viên', completed: true },
          { id: 'st-11', title: 'Khởi tạo VPN Gateway User', completed: true },
          { id: 'st-12', title: 'Gửi mã MFA 2FA token', completed: false },
        ],
      },
    ],
    timeline: [
      {
        key: 'SUBMITTED',
        title: 'Submitted',
        subTitle: 'Gửi yêu cầu',
        doneAt: '05/08/2026 14:30',
        note: 'Đã gửi từ Service Catalog portal.',
      },
      {
        key: 'MANAGER_APPROVAL',
        title: 'Manager Approval',
        subTitle: 'Duyệt Quản lý',
        doneAt: '05/08/2026 15:10',
        note: 'Đã được duyệt bởi Phạm Thị Dung.',
      },
      {
        key: 'IT_APPROVAL',
        title: 'IT Approval',
        subTitle: 'Duyệt IT',
        doneAt: '05/08/2026 16:45',
        note: 'Phê duyệt an toàn thông tin bởi Admin.',
      },
      {
        key: 'FULFILLMENT',
        title: 'Fulfillment',
        subTitle: 'Chuẩn bị & cấp phát',
        doneAt: '06/08/2026 08:15',
        note: 'Kỹ thuật viên Lê Minh Công đang xử lý profile VPN.',
      },
      {
        key: 'PROVISIONING',
        title: 'Provisioning',
        subTitle: 'Cấu hình hệ thống',
        note: 'Ghi nhận hạ tầng firewall gateway.',
      },
      {
        key: 'COMPLETED',
        title: 'Completed',
        subTitle: 'Hoàn tất',
        note: 'Gửi tài liệu hướng dẫn đăng nhập VPN.',
      },
    ],
  },
  {
    id: 'REQ-2026-00790',
    title: 'Xin máy in màu khổ A4 phòng Sales',
    category: 'Hardware',
    status: 'COMPLETED',
    priority: 'P2',
    createdAt: '01/08/2026 10:00',
    requester: 'Nguyễn Văn An',
    department: 'Sales & Marketing',
    costCenter: 'MKT-2026-009',
    description: 'Cấp máy in laser màu HP LaserJet Pro cho dự án in tài liệu đối tác.',
    items: [
      {
        id: 'FL-2026-0008',
        name: 'HP LaserJet Pro M454dn Printer',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        updatedAt: '03/08/2026 16:20',
        subTasks: [
          { id: 'st-20', title: 'Xuất kho thiết bị', completed: true },
          { id: 'st-21', title: 'Cấu hình IP tĩnh máy in', completed: true },
          { id: 'st-22', title: 'Bàn giao trực tiếp', completed: true },
        ],
      },
    ],
    timeline: [
      {
        key: 'SUBMITTED',
        title: 'Submitted',
        subTitle: 'Gửi yêu cầu',
        doneAt: '01/08/2026 10:00',
        note: 'Gửi thành công.',
      },
      {
        key: 'MANAGER_APPROVAL',
        title: 'Manager Approval',
        subTitle: 'Duyệt Quản lý',
        doneAt: '01/08/2026 11:30',
        note: 'Đã duyệt.',
      },
      {
        key: 'IT_APPROVAL',
        title: 'IT Approval',
        subTitle: 'Duyệt IT',
        doneAt: '01/08/2026 14:00',
        note: 'Phê duyệt ngân sách tài sản.',
      },
      {
        key: 'FULFILLMENT',
        title: 'Fulfillment',
        subTitle: 'Chuẩn bị & cấp phát',
        doneAt: '02/08/2026 09:00',
        note: 'Xuất kho và dán tem tài sản CMDB.',
      },
      {
        key: 'PROVISIONING',
        title: 'Provisioning',
        subTitle: 'Cấu hình hệ thống',
        doneAt: '03/08/2026 14:00',
        note: 'Đã map driver và cài IP tĩnh.',
      },
      {
        key: 'COMPLETED',
        title: 'Completed',
        subTitle: 'Hoàn tất',
        doneAt: '03/08/2026 16:20',
        note: 'Bàn giao thành công. Đã nghiệm thu 5★.',
      },
    ],
  },
  {
    id: 'REQ-2026-00755',
    title: 'Xin cấp quyền Admin máy trạm Dev',
    category: 'Access',
    status: 'REJECTED',
    priority: 'P3',
    createdAt: '28/07/2026 08:20',
    requester: 'Nguyễn Văn An',
    department: 'Phòng Kế Toán',
    costCenter: 'PRJ-2026-014',
    description: 'Yêu cầu cấp Local Admin trên Windows 11 để cài ứng dụng ngoài.',
    rejectionReason:
      'Không đủ điều kiện theo Chính sách an toàn thông tin ISO-27001 của công ty. Tài khoản kế toán không được phép cấp Local Admin.',
    items: [
      {
        id: 'FL-2026-0012',
        name: 'Local Administrator Rights Privilege',
        status: 'REJECTED',
        assignee: 'System Admin',
        updatedAt: '28/07/2026 10:15',
        subTasks: [
          { id: 'st-30', title: 'Đánh giá an toàn thông tin', completed: true },
          { id: 'st-31', title: 'Từ chối cấp quyền', completed: true },
        ],
      },
    ],
    timeline: [
      {
        key: 'SUBMITTED',
        title: 'Submitted',
        subTitle: 'Gửi yêu cầu',
        doneAt: '28/07/2026 08:20',
        note: 'Gửi từ portal.',
      },
      {
        key: 'MANAGER_APPROVAL',
        title: 'Manager Approval',
        subTitle: 'Duyệt Quản lý',
        doneAt: '28/07/2026 09:00',
        note: 'Đã gửi tới Ban An Ninh Thông Tin.',
      },
      {
        key: 'IT_APPROVAL',
        title: 'IT Approval',
        subTitle: 'Duyệt IT',
        doneAt: '28/07/2026 10:15',
        note: 'Từ chối bởi System Admin do vi phạm chính sách ISO-27001.',
      },
      {
        key: 'FULFILLMENT',
        title: 'Fulfillment',
        subTitle: 'Chuẩn bị & cấp phát',
        note: 'Đã hủy.',
      },
      {
        key: 'PROVISIONING',
        title: 'Provisioning',
        subTitle: 'Cấu hình hệ thống',
        note: 'Đã hủy.',
      },
      {
        key: 'COMPLETED',
        title: 'Completed',
        subTitle: 'Hoàn tất',
        note: 'Đã đóng ticket từ chối.',
      },
    ],
  },
];
