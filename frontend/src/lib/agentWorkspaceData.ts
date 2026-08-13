import {
  FileText,
  UserCheck,
  ShieldCheck,
  Package,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

export type TicketStatus =
  | 'NEW'
  | 'OPEN'
  | 'IN_PROGRESS'
  | 'ON_HOLD'
  | 'PENDING_CUSTOMER'
  | 'RESOLVED'
  | 'CLOSED';

export type PriorityKey = 'P0' | 'P1' | 'P2' | 'P3';
export type ImpactKey = 'HIGH' | 'MEDIUM' | 'LOW';

export interface TicketRequester {
  name: string;
  company: string;
  department: string;
  email: string;
}

export interface TicketSLA {
  name: string;
  dueAt: string;
  pct: number; // percentage remaining e.g. 68
}

export interface TicketDetail {
  id: string; // e.g. "INC-10582"
  title: string; // e.g. "VPN Authentication Failed"
  priority: PriorityKey;
  impact: ImpactKey;
  status: TicketStatus;
  requester: TicketRequester;
  asset?: string;
  sla: TicketSLA;
  category: string;
  urgency: string;
  createdBy: string;
  tags: string[];
  assignee: string;
  createdAt: string;
  description: string;
}

export interface ConversationItem {
  id: string;
  kind: 'USER' | 'TECH' | 'NOTE' | 'SYSTEM' | 'AI';
  author: string;
  time: string;
  body: string;
  internal?: boolean;
}

export type RelatedKind =
  | 'INCIDENT'
  | 'PROBLEM'
  | 'MAJOR_INCIDENT'
  | 'CHANGE'
  | 'SERVICE_REQUEST';

export interface RelatedRecord {
  id: string;
  kind: RelatedKind;
  title: string;
  status: string;
  linkedAt: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  detail: string;
  type: 'status' | 'note' | 'assignment' | 'priority' | 'system';
}

export const STATUS_META: Record<
  TicketStatus,
  {
    label: string;
    color: string;
    borderClass: string;
    bgClass: string;
    textClass: string;
    dotClass: string;
  }
> = {
  NEW: {
    label: 'Mới',
    color: '#22d3ee',
    borderClass: 'border-cyan-400/30',
    bgClass: 'bg-cyan-400/10',
    textClass: 'text-cyan-300',
    dotClass: 'bg-cyan-400',
  },
  OPEN: {
    label: 'Mở',
    color: '#3b82f6',
    borderClass: 'border-blue-400/30',
    bgClass: 'bg-blue-400/10',
    textClass: 'text-blue-300',
    dotClass: 'bg-blue-400',
  },
  IN_PROGRESS: {
    label: 'Đang xử lý',
    color: '#f59e0b',
    borderClass: 'border-amber-400/40',
    bgClass: 'bg-amber-400/10',
    textClass: 'text-amber-300',
    dotClass: 'bg-amber-400',
  },
  ON_HOLD: {
    label: 'Tạm hoãn',
    color: '#71717a',
    borderClass: 'border-zinc-500/30',
    bgClass: 'bg-zinc-500/10',
    textClass: 'text-zinc-400',
    dotClass: 'bg-zinc-400',
  },
  PENDING_CUSTOMER: {
    label: 'Chờ khách hàng',
    color: '#818cf8',
    borderClass: 'border-indigo-400/30',
    bgClass: 'bg-indigo-400/10',
    textClass: 'text-indigo-300',
    dotClass: 'bg-indigo-400',
  },
  RESOLVED: {
    label: 'Đã xử lý',
    color: '#14b8a6',
    borderClass: 'border-teal-400/30',
    bgClass: 'bg-teal-400/10',
    textClass: 'text-teal-300',
    dotClass: 'bg-teal-400',
  },
  CLOSED: {
    label: 'Đã đóng',
    color: '#10b981',
    borderClass: 'border-emerald-400/30',
    bgClass: 'bg-emerald-400/10',
    textClass: 'text-emerald-300',
    dotClass: 'bg-emerald-400',
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

export const IMPACT_META: Record<
  ImpactKey,
  { label: string; classNames: string }
> = {
  HIGH: { label: 'HIGH', classNames: 'bg-amber-500/20 border border-amber-500/40 text-amber-300 font-mono' },
  MEDIUM: { label: 'MEDIUM', classNames: 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 font-mono' },
  LOW: { label: 'LOW', classNames: 'bg-zinc-500/20 border border-zinc-500/40 text-zinc-400 font-mono' },
};

export const MOCK_TICKET_DETAIL: TicketDetail = {
  id: 'INC-10582',
  title: 'VPN Authentication Failed',
  priority: 'P2',
  impact: 'HIGH',
  status: 'IN_PROGRESS',
  category: 'Network / VPN',
  urgency: 'Medium',
  createdBy: 'Nguyen Van A',
  assignee: 'Lê Minh Công',
  createdAt: '06/08/2026 09:14',
  asset: 'AST-0723',
  tags: ['vpn', 'office-365', 'remote-work'],
  description:
    'Khách hàng báo không thể đăng nhập GlobalProtect VPN từ sáng nay. Thông báo lỗi: "Authentication failed. Certificate or Active Directory credentials rejected by Palo Alto Gateway". Ảnh hưởng trực tiếp đến làm việc từ xa của bộ phận Kế toán.',
  requester: {
    name: 'Nguyen Van A',
    company: 'Công ty ABC',
    department: 'Phòng Kế Toán',
    email: 'nguyenvana@company.vn',
  },
  sla: {
    name: 'SLA Response — P2 Medium',
    dueAt: '06/08/2026 15:30',
    pct: 68,
  },
};

export const MOCK_CONVERSATIONS: ConversationItem[] = [
  {
    id: 'msg-1',
    kind: 'USER',
    author: 'Nguyen Van A',
    time: '06/08 09:14',
    body: 'Chào IT, sáng nay tôi bật Palo Alto GlobalProtect VPN để làm việc từ nhà thì bị lỗi "Authentication Failed". Đã thử nhập lại password 3 lần nhưng không được. Nhờ hỗ trợ gấp giúp tôi!',
  },
  {
    id: 'msg-2',
    kind: 'SYSTEM',
    author: 'System',
    time: '06/08 09:15',
    body: 'Ticket chuyển từ Tech Queue tự động gán cho Lê Minh Công (Level 2 Support).',
  },
  {
    id: 'msg-3',
    kind: 'AI',
    author: 'AI Copilot',
    time: '06/08 09:16',
    body: 'Gợi ý từ AI: Phân loại sự cố là Network / VPN (độ tin cậy 87%). Bài viết KB liên quan: KB-0041 (VPN Auth Failed). Kiểm tra log NPS RADIUS server xem cổng 1812 có bị block không.',
  },
  {
    id: 'msg-4',
    kind: 'NOTE',
    author: 'Lê Minh Công',
    time: '06/08 09:30',
    body: 'Ghi chú nội bộ: Đã check NPS RADIUS server (192.168.10.15), dịch vụ NPS vẫn RUNNING. Khả năng cao tài khoản user bị lock trên Active Directory sau 3 lần gõ sai.',
    internal: true,
  },
  {
    id: 'msg-5',
    kind: 'TECH',
    author: 'Lê Minh Công',
    time: '06/08 09:35',
    body: 'Chào anh An, tôi đã tiếp nhận sự cố VPN. Tôi đang kiểm tra trạng thái tài khoản AD và cấu hình trên Firewall Gateway. Anh vui lòng chờ trong ít phút nhé.',
  },
];

export const MOCK_RELATED_RECORDS: RelatedRecord[] = [
  {
    id: 'INC-10570',
    kind: 'INCIDENT',
    title: 'VPN disconnect lặp lại tại chi nhánh HCM',
    status: 'Đã giải quyết',
    linkedAt: '06/08/2026 09:30',
  },
  {
    id: 'PRB-0081',
    kind: 'PROBLEM',
    title: 'Xung đột SSL Certificate trên Palo Alto Gateway',
    status: 'Đang điều tra',
    linkedAt: '06/08/2026 09:40',
  },
  {
    id: 'MI-0032',
    kind: 'MAJOR_INCIDENT',
    title: 'Nghẽn băng thông VPN Gateway giờ cao điểm',
    status: 'War Room Active',
    linkedAt: '06/08/2026 10:00',
  },
  {
    id: 'CHG-0214',
    kind: 'CHANGE',
    title: 'Nâng cấp Palo Alto PAN-OS 10.2.4 Patch',
    status: 'Chờ CAB duyệt',
    linkedAt: '06/08/2026 10:15',
  },
  {
    id: 'REQ-10291',
    kind: 'SERVICE_REQUEST',
    title: 'Xin cấp quyền VPN cho nhân viên mới',
    status: 'Đang fulfillment',
    linkedAt: '06/08/2026 10:30',
  },
];

export const MOCK_AUDIT_LOG: AuditEntry[] = [
  {
    id: 'aud-1',
    timestamp: '06/08/2026 09:35',
    actor: 'Lê Minh Công',
    action: 'Đổi trạng thái',
    detail: 'Chuyển trạng thái ticket từ OPEN → IN_PROGRESS.',
    type: 'status',
  },
  {
    id: 'aud-2',
    timestamp: '06/08/2026 09:30',
    actor: 'Lê Minh Công',
    action: 'Thêm ghi chú nội bộ',
    detail: 'Ghi chú: Kiểm tra NPS RADIUS server 192.168.10.15.',
    type: 'note',
  },
  {
    id: 'aud-3',
    timestamp: '06/08/2026 09:15',
    actor: 'System Auto-Router',
    action: 'Gán người xử lý',
    detail: 'Gán ticket cho kỹ thuật viên Lê Minh Công.',
    type: 'assignment',
  },
  {
    id: 'aud-4',
    timestamp: '06/08/2026 09:14',
    actor: 'Nguyen Van A',
    action: 'Khởi tạo Ticket',
    detail: 'Khởi tạo sự cố mới qua Email Gateway với mức ưu tiên P2.',
    type: 'system',
  },
];

export const MOCK_KB_SOURCES = [
  {
    id: 'KB-0041',
    title: 'VPN Auth Failed — Khắc phục lỗi Palo Alto GlobalProtect',
    matchPct: 92,
  },
  {
    id: 'KB-0028',
    title: 'Hướng dẫn Reset mật khẩu Active Directory cho user remote',
    matchPct: 84,
  },
  {
    id: 'KB-0105',
    title: 'Cấu hình RADIUS NPS Server & Certificate Chain',
    matchPct: 76,
  },
];

export const MOCK_SUGGESTED_STEPS = [
  'Kiểm tra trạng thái VPN Gateway và RADIUS service.',
  'Xác minh tài khoản AD bị khóa hoặc hết hạn password.',
  'Kiểm tra log NPS xem authentication attempt có đến không.',
  'Test kết nối bằng tài khoản test trước khi trả lời khách.',
];
