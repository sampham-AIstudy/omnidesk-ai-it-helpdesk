import { TicketCategory, TicketPriority, TicketStatus } from '@/types';
import { differenceInHours, differenceInMinutes, formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

export const VIETNAM_TIME_ZONE = 'Asia/Ho_Chi_Minh';

export function parseUtcDate(value: string | Date | null | undefined): Date {
  if (!value) return new Date();
  if (value instanceof Date) return value;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(trimmed)) {
      return new Date(trimmed.replace(' ', 'T') + 'Z');
    }
    return new Date(trimmed);
  }
  return new Date(value);
}

export function formatVietnamTime(
  value: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'short', timeStyle: 'short' },
): string {
  if (!value) return '';
  return new Intl.DateTimeFormat('vi-VN', { timeZone: VIETNAM_TIME_ZONE, ...options }).format(parseUtcDate(value));
}

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
  needs_clarification: 'Cần bổ sung thông tin',
  pending_hitl: 'Chờ duyệt',
  in_progress: 'Đang xử lý',
  waiting_for_agent: 'Chờ kỹ thuật viên',
  human_active: 'Đang xử lý thủ công',
  pending_closure: 'Chờ đóng',
  resolved: 'Đã xử lý',
  closed: 'Đã đóng',
  escalated: 'Leo thang',
  rejected: 'Từ chối',
  reopened: 'Mở lại',
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

export function getSLAStatus(slaDeadline: string | Date | null | undefined): 'ok' | 'warning' | 'danger' | 'none' {
  if (!slaDeadline) return 'none';
  const deadline = parseUtcDate(slaDeadline);
  const now = new Date();
  const hoursLeft = differenceInHours(deadline, now);
  if (hoursLeft < 0) return 'danger';
  if (hoursLeft < 2) return 'danger';
  if (hoursLeft < 4) return 'warning';
  return 'ok';
}

export function formatSLACountdown(slaDeadline: string | Date | null | undefined): string {
  if (!slaDeadline) return 'Chưa gán SLA';
  const deadline = parseUtcDate(slaDeadline);
  const now = new Date();
  const minutesLeft = differenceInMinutes(deadline, now);
  if (minutesLeft < 0) return `Trễ ${Math.abs(minutesLeft)}p`;
  if (minutesLeft < 60) return `Còn ${minutesLeft}p`;
  const h = Math.floor(minutesLeft / 60);
  const m = minutesLeft % 60;
  return `Còn ${h}h ${m}p`;
}

export function formatRelative(date: string | Date | null | undefined): string {
  if (!date) return '';
  return formatDistanceToNow(parseUtcDate(date), { addSuffix: true, locale: vi });
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
      label: 'Phân loại rõ',
      description: 'Đây là độ chắc chắn của bước phân loại, không phải mức độ đúng của câu trả lời hay mức độ phù hợp của nguồn.',
      color: 'var(--green)',
    };
  }
  if (score >= CONFIDENCE_WARNING_MIN) {
    return {
      band: 'warning',
      label: 'Phân loại cần rà soát',
      description: 'Đây là độ chắc chắn của bước phân loại; quyết định xử lý vẫn cần dựa vào evidence và workflow.',
      color: 'var(--amber)',
    };
  }
  return {
    band: 'manual',
    label: 'Cần xác minh phân loại',
    description: 'Độ chắc chắn phân loại thấp; kỹ thuật viên cần xác minh trước khi xử lý.',
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

/**
 * Cleans raw ticket description containing metadata tags and base64 image strings
 * into a neat, human-readable one-line summary for card previews.
 */
export function cleanTicketDescriptionSummary(desc: string | null | undefined): string {
  if (!desc) return '';
  let res = desc;

  // Extract actual user description if "---" is present
  if (res.includes('---')) {
    const parts = res.split('---');
    const actual = parts[parts.length - 1]?.trim();
    if (actual) {
      const withoutPrefix = actual.replace(/^(?:MÔ TẢ CHI TIẾT SỰ CỐ|Chi tiết sự cố)\s*[:\-\n]*/i, '').trim();
      if (withoutPrefix) res = withoutPrefix;
    }
  }

  // Strip attachment tags
  res = res.replace(/\[Đính Kèm Ảnh:\s*[^|\]]+(?:\|[^\]]*)?\]/g, '📷 [Ảnh đính kèm]');
  res = res.replace(/\[Đính Kèm(?: Tệp)?:\s*[^\]]+\]/g, '📎 [Tệp đính kèm]');

  // Strip metadata brackets like [Hệ Thống / Dịch Vụ: ...]
  res = res.replace(/\[(?:Hệ Thống|Phân Loại|Mức Độ|Mã Sự Cố|Môi Trường|Vị Trí)[^\]]+\]\s*/gi, '');

  // Strip dangling base64 image strings if any
  res = res.replace(/data:image\/[a-zA-Z0-9+]+;base64,[A-Za-z0-9+/=]+/g, '');

  // Clean up whitespace
  return res.replace(/\s+/g, ' ').trim();
}
