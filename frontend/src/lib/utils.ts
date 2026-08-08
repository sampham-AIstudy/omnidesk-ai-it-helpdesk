import { TicketCategory, TicketPriority, TicketStatus } from '@/types';
import { differenceInHours, differenceInMinutes, formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

export const CATEGORY_LABELS: Record<TicketCategory, string> = {
  network: 'Mạng / VPN',
  software: 'Phần mềm',
  hardware: 'Phần cứng',
  access_permission: 'Quyền truy cập',
  email: 'Email',
  erp_sap: 'ERP / SAP',
  security: 'Bảo mật',
  hr_system: 'HR System',
  infrastructure: 'Hạ tầng',
  other: 'Khác',
};

export const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: 'Thấp',
  medium: 'Trung bình',
  high: 'Cao',
  critical: 'Khẩn cấp',
};

export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Mới',
  classifying: 'AI đang đọc',
  pending_hitl: 'Chờ duyệt',
  in_progress: 'Đang xử lý',
  pending_closure: 'Chờ đóng',
  resolved: 'Đã xử lý',
  closed: 'Đã đóng',
  escalated: 'Leo thang',
  rejected: 'Từ chối',
};

export const COMPANY_LABELS: Record<string, string> = {
  real_estate: 'BĐS X',
  automotive: 'Xe X',
  healthcare: 'Y tế X',
  corporate: 'Tập đoàn',
};

export const ROLE_LABELS: Record<string, string> = {
  employee: 'Nhân viên',
  technician: 'Kỹ thuật viên',
  manager: 'Quản lý',
  admin: 'Quản trị',
};

export function getSLAStatus(slaDeadline: string | null): 'ok' | 'warning' | 'danger' | 'none' {
  if (!slaDeadline) return 'none';
  const deadline = new Date(slaDeadline);
  const now = new Date();
  const hoursLeft = differenceInHours(deadline, now);
  if (hoursLeft < 0) return 'danger';
  if (hoursLeft < 2) return 'danger';
  if (hoursLeft < 4) return 'warning';
  return 'ok';
}

export function formatSLACountdown(slaDeadline: string | null): string {
  if (!slaDeadline) return 'Chưa gán SLA';
  const deadline = new Date(slaDeadline);
  const now = new Date();
  const minutesLeft = differenceInMinutes(deadline, now);
  if (minutesLeft < 0) return `Trễ ${Math.abs(minutesLeft)}p`;
  if (minutesLeft < 60) return `Còn ${minutesLeft}p`;
  const h = Math.floor(minutesLeft / 60);
  const m = minutesLeft % 60;
  return `Còn ${h}h ${m}p`;
}

export function formatRelative(date: string): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: vi });
}

export const CONFIDENCE_AUTO_MIN = 0.75;
export const CONFIDENCE_WARNING_MIN = 0.60;

export type ConfidenceBand = 'unavailable' | 'normal' | 'warning' | 'manual';

export interface ConfidencePresentation {
  band: ConfidenceBand;
  label: string;
  description: string;
  color: string;
}

export function getConfidencePresentation(score: number | null | undefined): ConfidencePresentation {
  if (score === null || score === undefined) {
    return {
      band: 'unavailable',
      label: 'Chưa có',
      description: 'Agent chưa hoàn tất phân loại.',
      color: 'var(--text-muted)',
    };
  }
  if (score >= CONFIDENCE_AUTO_MIN) {
    return {
      band: 'normal',
      label: 'Đủ tin cậy',
      description: 'Agent có thể xử lý bình thường nếu không có điều kiện HITL độc lập.',
      color: 'var(--green)',
    };
  }
  if (score >= CONFIDENCE_WARNING_MIN) {
    return {
      band: 'warning',
      label: 'Cần lưu ý',
      description: 'Bạn có thể thử giải pháp hoặc yêu cầu người hỗ trợ trực tiếp.',
      color: 'var(--amber)',
    };
  }
  return {
    band: 'manual',
    label: 'Xử lý thủ công',
    description: 'Ticket bắt buộc được chuyển cho đội IT Support.',
    color: 'var(--red)',
  };
}

export function getConfidenceColor(score: number | null): string {
  return getConfidencePresentation(score).color;
}

export function getErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: unknown; message?: string } } };
    const detail = e.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item)))
        .join(', ');
    }
    if (detail && typeof detail === 'object') {
      return (detail as { msg?: string }).msg || JSON.stringify(detail);
    }
    if (e.response?.data?.message) {
      return e.response.data.message;
    }
  }
  if (err && typeof err === 'object' && 'message' in err) {
    const msg = (err as { message?: string }).message;
    if (msg === 'Network Error') {
      return 'Lỗi kết nối: Không thể kết nối tới Server Backend (port 8000). Vui lòng kiểm tra lại xem Backend (python run.py) có đang chạy không.';
    }
    if (msg) return msg;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'Đã xảy ra lỗi';
}


