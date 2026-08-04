'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Bot, CheckCircle2, Clock, Inbox, Loader2, ShieldAlert } from 'lucide-react';
import { TicketPriority, TicketStatus } from '@/types';
import { PRIORITY_LABELS, STATUS_LABELS } from '@/lib/utils';

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] ?? status}</span>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <span className={`badge badge-${priority}`}>{PRIORITY_LABELS[priority] ?? priority}</span>;
}

export function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="muted" style={{ fontSize: 12 }}>Chua co</span>;

  const pct = Math.round(score * 100);
  const color = score >= 0.85 ? 'var(--green)' : score >= 0.6 ? 'var(--amber)' : 'var(--red)';
  const label = score >= 0.85 ? 'Cao' : score >= 0.6 ? 'Can xem lai' : 'Thap';

  return (
    <div style={{ minWidth: 112 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ color, fontSize: 11, fontWeight: 800 }}>{label}</span>
        <span className="muted" style={{ fontSize: 11 }}>{pct}%</span>
      </div>
      <div className="confidence-bar">
        <div className="confidence-fill" style={{ width: `${pct}%`, background: color }} />
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
  return <Loader2 className="spin" size={size} />;
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
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, letterSpacing: 0 }}>{title}</h1>
        {subtitle && <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 13 }}>{subtitle}</p>}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  );
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
