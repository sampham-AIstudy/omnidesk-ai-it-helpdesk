import {
  Wrench,
  PackageCheck,
  CheckCircle2,
  Loader2,
  OctagonAlert,
  Circle,
  FileClock,
} from 'lucide-react';

export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED';

export interface FulfillmentTask {
  id: string;            // e.g. "FL-2026-0001"
  name: string;          // e.g. "Create Entra ID account"
  group: string;         // e.g. "Active Directory"
  status: TaskStatus;
  assignee?: string;     // e.g. "Lê Minh Công"
  order: number;
  parallel: boolean;     // true = parallel step, false = sequential step
  dependsOn?: string[];  // array of task IDs that must complete first
  dueDate?: string;
  notes?: string;        // completion result / serial / license key
  blockedReason?: string;
}

export type PriorityKey = 'P0' | 'P1' | 'P2' | 'P3';

export interface FulfillmentActivity {
  id: string;
  timestamp: string;
  actor: string;
  message: string;
  statusColor?: string;
}

export interface RequestFulfillment {
  id: string;            // e.g. "REQ-10291"
  title: string;         // e.g. "New Employee Onboarding"
  category: string;      // e.g. "Onboarding"
  priority: PriorityKey;
  createdAt: string;     // "06/08/2026 09:14"
  startDate: string;     // "12/08/2026"
  requester: string;     // "Nguyen Van A"
  department: string;    // "Finance"
  costCenter: string;    // "PRJ-2026-014"
  description: string;
  assignee: string;      // "Lê Minh Công"
  updatedAt: string;
  tasks: FulfillmentTask[];
  activities: FulfillmentActivity[];
}

export const TASK_STATUS_META: Record<
  TaskStatus,
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
  PENDING: {
    label: 'Chờ xử lý',
    icon: Circle,
    color: '#a1a1aa',
    borderClass: 'border-zinc-500/30',
    bgClass: 'bg-zinc-500/10',
    textClass: 'text-zinc-400',
    dotClass: 'bg-zinc-400',
  },
  IN_PROGRESS: {
    label: 'Đang xử lý',
    icon: Loader2,
    color: '#22d3ee',
    borderClass: 'border-cyan-400/40',
    bgClass: 'bg-cyan-400/10',
    textClass: 'text-cyan-300',
    dotClass: 'bg-cyan-400',
  },
  COMPLETED: {
    label: 'Hoàn tất',
    icon: CheckCircle2,
    color: '#34d399',
    borderClass: 'border-emerald-400/30',
    bgClass: 'bg-emerald-400/10',
    textClass: 'text-emerald-300',
    dotClass: 'bg-emerald-400',
  },
  BLOCKED: {
    label: 'Bị chặn',
    icon: OctagonAlert,
    color: '#f87171',
    borderClass: 'border-red-400/40',
    bgClass: 'bg-red-400/10',
    textClass: 'text-red-300',
    dotClass: 'bg-red-400',
  },
};

export const PRIORITY_META: Record<
  PriorityKey,
  { label: string; classNames: string }
> = {
  P0: { label: 'P0', classNames: 'bg-red-500/20 border border-red-500/40 text-red-300 font-mono' },
  P1: { label: 'P1', classNames: 'bg-orange-500/20 border border-orange-500/40 text-orange-300 font-mono' },
  P2: { label: 'P2', classNames: 'bg-amber-500/20 border border-amber-500/40 text-amber-300 font-mono' },
  P3: { label: 'P3', classNames: 'bg-zinc-500/20 border border-zinc-500/40 text-zinc-400 font-mono' },
};

export function deriveRequestStatus(tasks: FulfillmentTask[]): TaskStatus {
  if (tasks.length === 0) return 'PENDING';
  const allCompleted = tasks.every((t) => t.status === 'COMPLETED');
  if (allCompleted) return 'COMPLETED';
  const anyBlocked = tasks.some((t) => t.status === 'BLOCKED');
  if (anyBlocked) return 'BLOCKED';
  const anyInProgress = tasks.some((t) => t.status === 'IN_PROGRESS');
  if (anyInProgress) return 'IN_PROGRESS';
  return 'PENDING';
}

export const MOCK_WORKBENCH_REQUESTS: RequestFulfillment[] = [
  {
    id: 'REQ-10291',
    title: 'New Employee Onboarding',
    category: 'Onboarding',
    priority: 'P0',
    createdAt: '06/08/2026 09:14',
    startDate: '12/08/2026',
    requester: 'Nguyen Van A',
    department: 'Finance',
    costCenter: 'PRJ-2026-014',
    description:
      'Setup toàn bộ tài nguyên CNTT cho nhân viên mới: tài khoản, license, thiết bị và quyền truy cập trước ngày bắt đầu 12/08/2026.',
    assignee: 'Lê Minh Công',
    updatedAt: '06/08/2026 14:20',
    tasks: [
      {
        id: 'FL-2026-0001',
        name: 'Create Entra ID account',
        group: 'Active Directory',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 1,
        parallel: false,
        dueDate: '11/08/2026',
        notes: 'User UPN: nguyen.van.a@company.com (OU: Finance)',
      },
      {
        id: 'FL-2026-0002',
        name: 'Assign Microsoft 365',
        group: 'License Provisioning',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 2,
        parallel: false,
        dependsOn: ['FL-2026-0001'],
        dueDate: '11/08/2026',
        notes: 'M365 Business Premium assigned via Group Rule.',
      },
      {
        id: 'FL-2026-0003',
        name: 'Create VPN account',
        group: 'Network Security',
        status: 'IN_PROGRESS',
        assignee: 'Lê Minh Công',
        order: 3,
        parallel: true,
        dependsOn: ['FL-2026-0001'],
        dueDate: '11/08/2026',
        notes: 'Đang tạo profile SSL VPN trên Palo Alto Firewall.',
      },
      {
        id: 'FL-2026-0004',
        name: 'Prepare Laptop',
        group: 'Hardware Inventory',
        status: 'IN_PROGRESS',
        assignee: 'Lê Minh Công',
        order: 3,
        parallel: true,
        dueDate: '11/08/2026',
        notes: 'Dell Latitude 5440 (Serial: DL-99201-VN) đang cài Win 11 Pro.',
      },
      {
        id: 'FL-2026-0005',
        name: 'Add Finance shared drive',
        group: 'Storage Access',
        status: 'PENDING',
        assignee: 'Lê Minh Công',
        order: 4,
        parallel: false,
        dependsOn: ['FL-2026-0001'],
        dueDate: '12/08/2026',
      },
    ],
    activities: [
      {
        id: 'act-1',
        timestamp: '06/08/2026 14:20',
        actor: 'Lê Minh Công',
        message: 'đã cập nhật "Create Entra ID account" thành Hoàn tất.',
        statusColor: '#34d399',
      },
      {
        id: 'act-2',
        timestamp: '06/08/2026 13:55',
        actor: 'Lê Minh Công',
        message: 'bắt đầu xử lý "Assign Microsoft 365".',
        statusColor: '#22d3ee',
      },
      {
        id: 'act-3',
        timestamp: '06/08/2026 09:14',
        actor: 'Nguyen Van A',
        message: 'gửi yêu cầu (tự động tạo 5 fulfillment tasks).',
        statusColor: '#a1a1aa',
      },
    ],
  },
  {
    id: 'REQ-10285',
    title: 'Cấp quyền truy cập hệ thống ERP SAP',
    category: 'Access',
    status: 'BLOCKED',
    priority: 'P1',
    createdAt: '05/08/2026 11:20',
    startDate: '05/08/2026',
    requester: 'Trần Thị Bích',
    department: 'Ban Giám Đốc',
    costCenter: 'BOD-2026-001',
    description: 'Cấp quyền SAP FI-CO module cho kế toán trưởng giám sát ngân sách.',
    assignee: 'Lê Minh Công',
    updatedAt: '06/08/2026 10:15',
    tasks: [
      {
        id: 'FL-2026-0010',
        name: 'Kiểm tra duyệt SOD (Segregation of Duties)',
        group: 'Compliance Security',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 1,
        parallel: false,
        dueDate: '05/08/2026',
        notes: 'SOD Check PASS không xung đột quyền.',
      },
      {
        id: 'FL-2026-0011',
        name: 'Khởi tạo SAP User & Gán Role FI-CO',
        group: 'SAP Basis Team',
        status: 'BLOCKED',
        assignee: 'Lê Minh Công',
        order: 2,
        parallel: false,
        dependsOn: ['FL-2026-0010'],
        dueDate: '06/08/2026',
        blockedReason: 'Chờ bên SAP Basis cấp bổ sung SAP Named License còn thiếu.',
      },
    ],
    activities: [
      {
        id: 'act-10',
        timestamp: '06/08/2026 10:15',
        actor: 'Lê Minh Công',
        message: 'đã đánh dấu "Khởi tạo SAP User" Bị chặn: Chờ bên SAP Basis cấp bổ sung SAP Named License.',
        statusColor: '#f87171',
      },
    ],
  },
  {
    id: 'REQ-10270',
    title: 'Cấp mới Laptop ThinkPad X1 Carbon',
    category: 'Hardware',
    status: 'IN_PROGRESS',
    priority: 'P1',
    createdAt: '04/08/2026 15:00',
    startDate: '04/08/2026',
    requester: 'Phạm Thị Dung',
    department: 'IT Department',
    costCenter: 'IT-2026-001',
    description: 'Đổi máy laptop cũ hỏng cho Trưởng phòng IT.',
    assignee: 'Lê Minh Công',
    updatedAt: '06/08/2026 11:30',
    tasks: [
      {
        id: 'FL-2026-0020',
        name: 'Xuất kho ThinkPad X1 Carbon Gen 11',
        group: 'IT Asset Store',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 1,
        parallel: false,
        notes: 'Serial: TP-X1-88421-VN',
      },
      {
        id: 'FL-2026-0021',
        name: 'Backup dữ liệu máy cũ & Transfer',
        group: 'Desktop Support',
        status: 'IN_PROGRESS',
        assignee: 'Lê Minh Công',
        order: 2,
        parallel: false,
        dependsOn: ['FL-2026-0020'],
        notes: 'Đang dùng OneDrive Migration Tool chuyển 120GB.',
      },
    ],
    activities: [
      {
        id: 'act-20',
        timestamp: '06/08/2026 11:30',
        actor: 'Lê Minh Công',
        message: 'đã hoàn thành xuất kho ThinkPad X1 Carbon.',
        statusColor: '#34d399',
      },
    ],
  },
  {
    id: 'REQ-10262',
    title: 'Xin phần mềm Adobe Creative Cloud',
    category: 'Software',
    status: 'COMPLETED',
    priority: 'P2',
    createdAt: '02/08/2026 08:30',
    startDate: '02/08/2026',
    requester: 'Hoàng Văn Cường',
    department: 'Marketing',
    costCenter: 'MKT-2026-003',
    description: 'Cấp Adobe Creative Cloud All Apps cho Designer làm truyền thông.',
    assignee: 'Lê Minh Công',
    updatedAt: '03/08/2026 16:00',
    tasks: [
      {
        id: 'FL-2026-0030',
        name: 'Gán Adobe VIP License ID',
        group: 'Software Admin',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 1,
        parallel: false,
        notes: 'Assigned hoang.cuong@company.com via Adobe Admin Console.',
      },
      {
        id: 'FL-2026-0031',
        name: 'Gửi email hướng dẫn kích hoạt',
        group: 'Support Desk',
        status: 'COMPLETED',
        assignee: 'Lê Minh Công',
        order: 2,
        parallel: false,
        dependsOn: ['FL-2026-0030'],
        notes: 'Email sent automatically.',
      },
    ],
    activities: [
      {
        id: 'act-30',
        timestamp: '03/08/2026 16:00',
        actor: 'Lê Minh Công',
        message: 'đã hoàn tất toàn bộ 2 fulfillment tasks.',
        statusColor: '#34d399',
      },
    ],
  },
];
