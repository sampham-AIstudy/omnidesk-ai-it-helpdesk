'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { AlertTriangle, Bot, CheckCircle2, Clock, Inbox, Loader2, Search, ShieldAlert, X } from 'lucide-react';
import { TicketPriority, TicketStatus } from '@/types';
import { getConfidencePresentation, PRIORITY_LABELS, STATUS_LABELS } from '@/lib/utils';

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge-${status}`}><span className="status-dot" aria-hidden="true" />{STATUS_LABELS[status] ?? status}</span>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <span className={`badge badge-${priority}`}>{PRIORITY_LABELS[priority] ?? priority}</span>;
}

export function ConfidenceBadge({ score }: { score: number | null }) {
  const presentation = getConfidencePresentation(score);
  if (score === null) {
    return <span className="muted" style={{ fontSize: 12 }}>{presentation.label}</span>;
  }

  const pct = Math.round(score * 100);

  return (
    <div style={{ minWidth: 128 }} title={presentation.description}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ color: presentation.color, fontSize: 11, fontWeight: 800 }}>{presentation.label}</span>
        <span className="muted" style={{ fontSize: 11 }}>{pct}%</span>
      </div>
      <div className="confidence-bar" role="progressbar" aria-label={`Độ chắc chắn phân loại: ${pct}% — ${presentation.label}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <div className="confidence-fill" style={{ width: `${pct}%`, background: presentation.color }} />
      </div>
    </div>
  );
}

export function SLABadge({ deadline }: { deadline: string | null }) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  if (!deadline) return <span className="muted" style={{ fontSize: 12 }}>Chua gan SLA</span>;

  const ms = new Date(deadline).getTime() - nowMs;
  const mins = Math.floor(ms / 60000);
  const statusClass = ms < 0 || ms < 7200000 ? 'sla-danger' : ms < 14400000 ? 'sla-warning' : 'sla-ok';

  let display: string;
  if (ms < 0) {
    const absM = Math.abs(mins);
    display = absM < 60 ? `Tre ${absM}p` : `Tre ${Math.floor(absM / 60)}h ${absM % 60}p`;
  } else if (mins < 60) {
    display = `Con ${mins}p`;
  } else {
    display = `Con ${Math.floor(mins / 60)}h ${mins % 60}p`;
  }

  return (
    <span className={statusClass} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 800 }}>
      <Clock size={13} />
      {display}
    </span>
  );
}

export function HITLBadge({ required }: { required: boolean }) {
  if (!required) return null;
  return (
    <span className="badge badge-pending_hitl">
      <ShieldAlert size={12} />
      HITL
    </span>
  );
}

export function VIPBadge() {
  return (
    <span className="badge badge-medium">
      VIP
    </span>
  );
}

export function Spinner({ size = 18 }: { size?: number }) {
  return <Loader2 className="spin" size={size} aria-hidden="true" />;
}

export function Skeleton({ height = 16, width = '100%' }: { height?: number; width?: number | string }) {
  return <span className="skeleton" aria-hidden="true" style={{ display: 'block', height, width }} />;
}

export function QueryError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card query-error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <div style={{ fontWeight: 800 }}>Không tải được dữ liệu</div>
        <div style={{ fontSize: 13, marginTop: 4 }}>{message}</div>
        {onRetry && <button className="btn-ghost" style={{ marginTop: 12 }} onClick={onRetry}>Thử lại</button>}
      </div>
    </div>
  );
}

export function FormField({
  label,
  required,
  error,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: (props: { id: string; describedBy?: string; invalid: boolean }) => React.ReactNode;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint && <div id={hintId} className="field-hint">{hint}</div>}
      {error && <div id={errorId} className="field-error" role="alert">{error}</div>}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Xác nhận',
  destructive = false,
  pending = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  destructive?: boolean;
  pending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const titleId = useId();
  const descriptionId = useId();
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    confirmRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !pending) onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previous?.focus();
    };
  }, [onClose, open, pending]);

  if (!open) return null;
  return (
    <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && !pending && onClose()}>
      <section className="modal-box confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId}>
        <h2 id={titleId}>{title}</h2>
        <p id={descriptionId}>{description}</p>
        <div className="dialog-actions">
          <button className="btn-ghost" disabled={pending} onClick={onClose}>Hủy</button>
          <button ref={confirmRef} className={destructive ? 'btn-danger' : 'btn-primary'} disabled={pending} onClick={onConfirm}>
            {pending && <Spinner size={15} />}{confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

export function Pagination({ page, pageSize, total, onPageChange }: { page: number; pageSize: number; total: number; onPageChange: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav className="pagination" aria-label="Phân trang">
      <span>{total === 0 ? '0 kết quả' : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} trên ${total}`}</span>
      <div>
        <button className="btn-ghost" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Trang trước</button>
        <span aria-current="page">Trang {page}/{pages}</span>
        <button className="btn-ghost" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Trang sau</button>
      </div>
    </nav>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action && <div className="page-header-action">{action}</div>}
    </div>
  );
}

export function ContentCard({
  title,
  description,
  action,
  children,
  className = '',
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`content-card ${className}`}>
    {(title || description || action) && <header className="content-card-header"><div>{title && <h2>{title}</h2>}{description && <p>{description}</p>}</div>{action && <div>{action}</div>}</header>}
    {children}
  </section>;
}

export function MetricCard({ label, value, detail, tone = 'neutral' }: { label: string; value: React.ReactNode; detail?: React.ReactNode; tone?: 'neutral' | 'info' | 'success' | 'warning' | 'danger' }) {
  return <section className={`metric-card metric-card--${tone}`}><p>{label}</p><strong>{value}</strong>{detail && <span>{detail}</span>}</section>;
}

export function DataToolbar({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Tìm kiếm',
  filters,
  activeFilters,
  onClearFilters,
  actions,
}: {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  filters?: React.ReactNode;
  activeFilters?: React.ReactNode;
  onClearFilters?: () => void;
  actions?: React.ReactNode;
}) {
  return <div className="data-toolbar"><div className="data-toolbar-main"><label className="toolbar-search"><Search size={16} aria-hidden="true" /><span className="sr-only">{searchPlaceholder}</span><input value={searchValue} onChange={(event) => onSearchChange(event.target.value)} placeholder={searchPlaceholder} /></label>{filters}</div>{actions && <div className="data-toolbar-actions">{actions}</div>}{activeFilters && <div className="active-filters">{activeFilters}{onClearFilters && <button type="button" className="btn-ghost btn-sm" onClick={onClearFilters}><X size={14} />Xóa bộ lọc</button>}</div>}</div>;
}

export function EmptyState({
  icon = 'inbox',
  title,
  desc,
  action,
}: {
  icon?: 'inbox' | 'check' | 'bot' | 'warning' | string;
  title: string;
  desc?: string;
  action?: React.ReactNode;
}) {
  const Icon =
    icon === 'check' ? CheckCircle2 :
    icon === 'bot' ? Bot :
    icon === 'warning' ? AlertTriangle :
    Inbox;

  return (
    <div style={{ textAlign: 'center', padding: '34px 18px', color: 'var(--text-secondary)' }}>
      <div style={{ width: 42, height: 42, borderRadius: 8, background: 'var(--surface-muted)', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
        <Icon size={21} />
      </div>
      <div style={{ color: 'var(--text)', fontSize: 14, fontWeight: 800, marginBottom: 4 }}>{title}</div>
      {desc && <div style={{ fontSize: 13, lineHeight: 1.5, maxWidth: 360, margin: '0 auto' }}>{desc}</div>}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  );
}
