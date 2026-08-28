import Link from 'next/link';
import { ArrowRight, Bot, Clock, GitBranch, Pin, ShieldAlert, Sparkles, User } from 'lucide-react';
import { Ticket } from '@/types';
import { CATEGORY_LABELS, formatRelative } from '@/lib/utils';
import { ConfidenceBadge, HITLBadge, PriorityBadge, SLABadge, StatusBadge } from './ui';

interface Props {
  ticket: Ticket;
  linkTo?: string;
  onApprove?: (ticket: Ticket) => void;
  onTogglePin?: (ticket: Ticket) => void;
  onContextMenu?: (
    e: Pick<React.MouseEvent, 'clientX' | 'clientY' | 'preventDefault'>,
    ticket: Ticket,
  ) => void;
  compact?: boolean;
  selected?: boolean;
  onClick?: () => void;
  queue?: boolean;
  showSla?: boolean;
}

export default function TicketCard({
  ticket,
  linkTo,
  onApprove,
  onTogglePin,
  onContextMenu,
  compact,
  selected,
  onClick,
  queue,
  showSla = true,
}: Props) {
  const card = (
    <div
      className="card ticket-card-item"
      onClick={onClick}
      onContextMenu={(e) => {
        if (onContextMenu) {
          e.preventDefault();
          onContextMenu(e, ticket);
        }
      }}
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.shiftKey && e.key === 'F10') || e.key === 'ContextMenu') {
          if (onContextMenu) {
            e.preventDefault();
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
            onContextMenu({ clientX: rect.left + 24, clientY: rect.top + 24, preventDefault: () => {} }, ticket);
          }
        }
      }}
      style={{
        padding: compact ? '10px 12px' : '12px 14px',
        cursor: linkTo || onClick ? 'pointer' : 'default',
        borderColor: selected ? 'var(--primary)' : ticket.is_pinned ? '#f59e0b' : 'var(--border-default)',
        borderLeft: ticket.is_pinned ? '4px solid #f59e0b' : selected ? '4px solid var(--primary)' : undefined,
        background: selected ? 'var(--primary-soft)' : ticket.is_pinned ? 'var(--amber-soft, #fffbeb)' : 'var(--surface)',
        outline: 'none',
        transition: 'all 120ms ease',
        borderRadius: 12,
        boxShadow: selected ? '0 0 0 1px var(--primary)' : 'none',
      }}
    >
      {/* Tier 1: Badges, ID, Pin & SLA Countdown */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {ticket.is_pinned && (
            <span
              style={{
                background: '#fef3c7',
                color: '#92400e',
                border: '1px solid #fde68a',
                borderRadius: 5,
                padding: '1px 6px',
                fontSize: 10.5,
                fontWeight: 800,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
              }}
            >
              📌 TOP
            </span>
          )}
          <span style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--text-muted)' }}>{ticket.ticket_number}</span>
          <StatusBadge status={ticket.status} />
          {ticket.priority && <PriorityBadge priority={ticket.priority} />}
          <HITLBadge required={ticket.hitl_required} />
          {showSla && ticket.sla_escalated && (
            <span className="badge badge-escalated" style={{ fontSize: 10, padding: '1px 6px' }}>
              SLA Vi phạm
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {showSla && <SLABadge deadline={ticket.sla_deadline} />}
          {onTogglePin && (
            <button
              type="button"
              aria-label={ticket.is_pinned ? 'Bỏ ghim' : 'Ghim lên đầu'}
              aria-pressed={ticket.is_pinned}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onTogglePin(ticket);
              }}
              style={{
                padding: '2px 6px',
                borderRadius: 6,
                border: '1px solid',
                borderColor: ticket.is_pinned ? '#f59e0b' : 'var(--border-default)',
                background: ticket.is_pinned ? '#fef3c7' : 'transparent',
                color: ticket.is_pinned ? '#92400e' : 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: 11,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                fontWeight: 700,
              }}
              title={ticket.is_pinned ? 'Bỏ ghim ưu tiên' : 'Ghim lên đầu hàng đợi'}
            >
              <Pin size={11} color={ticket.is_pinned ? '#b45309' : 'currentColor'} />
            </button>
          )}
        </div>
      </div>

      {/* Tier 2: Ticket Title */}
      <div
        style={{
          fontSize: 13.5,
          fontWeight: 800,
          color: 'var(--text-primary)',
          lineHeight: 1.35,
          marginBottom: 6,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {ticket.title}
      </div>

      {/* Tier 3: Submitter info, Category, Routing, Confidence & Time */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
          color: 'var(--text-muted)',
          fontSize: 11.5,
        }}
      >
        {/* Submitter */}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--text-secondary)', fontWeight: 600 }}>
          <User size={12} style={{ opacity: 0.7 }} />
          <span>
            {(ticket.created_by_user || ticket.submitter)?.full_name || (ticket.submitter_id ? `Nhân viên #${ticket.submitter_id}` : 'Người dùng')}
            {(ticket.created_by_user || ticket.submitter)?.department ? ` (${(ticket.created_by_user || ticket.submitter)?.department})` : ''}
          </span>
        </span>

        {/* Category */}
        {ticket.category && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', background: 'var(--surface-subtle)', borderRadius: 4, border: '1px solid var(--border-subtle)' }}>
            📁 {CATEGORY_LABELS[ticket.category]}
          </span>
        )}

        {/* Routing Target */}
        {ticket.routing_target && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#047857', background: '#ecfdf5', padding: '1px 6px', borderRadius: 4, border: '1px solid #a7f3d0', fontWeight: 600 }}>
            <GitBranch size={11} />
            {ticket.routing_target}
          </span>
        )}

        {/* AI Confidence */}
        {ticket.confidence_score != null && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: ticket.confidence_score >= 0.8 ? '#047857' : '#b45309' }}>
            <Sparkles size={11} />
            {Math.round(ticket.confidence_score * 100)}% AI
          </span>
        )}

        {/* Created time */}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, marginLeft: 'auto' }}>
          <Clock size={11} />
          {formatRelative(ticket.created_at)}
        </span>

        {onApprove && ticket.status === 'pending_hitl' && (
          <button
            className="btn-primary"
            style={{ padding: '2px 8px', height: 24, fontSize: 11 }}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onApprove(ticket);
            }}
          >
            <ShieldAlert size={12} />
            Duyệt
          </button>
        )}
      </div>
    </div>
  );

  if (linkTo) {
    return <Link href={linkTo} style={{ textDecoration: 'none' }}>{card}</Link>;
  }

  return card;
}
