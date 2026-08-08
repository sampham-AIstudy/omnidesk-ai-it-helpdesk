'use client';

import Link from 'next/link';
import { ArrowRight, Bot, GitBranch, ShieldAlert } from 'lucide-react';
import { Ticket } from '@/types';
import { CATEGORY_LABELS, formatRelative } from '@/lib/utils';
import { ConfidenceBadge, HITLBadge, PriorityBadge, SLABadge, StatusBadge } from './ui';

interface Props {
  ticket: Ticket;
  linkTo?: string;
  onApprove?: (ticket: Ticket) => void;
  compact?: boolean;
  selected?: boolean;
  onClick?: () => void;
}

export default function TicketCard({ ticket, linkTo, onApprove, compact, selected, onClick }: Props) {
  const card = (
    <div
      className="card"
      onClick={onClick}
      style={{
        padding: compact ? 12 : 14,
        cursor: linkTo || onClick ? 'pointer' : 'default',
        borderColor: selected ? 'var(--primary)' : 'var(--border)',
        background: selected ? 'var(--primary-soft)' : 'var(--surface)',
      }}
    >
      <div className="ticket-card-grid" style={{ display: 'grid', gridTemplateColumns: compact ? '1fr auto' : 'minmax(0, 1fr) 210px', gap: 14, alignItems: 'start' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text)' }}>{ticket.ticket_number}</span>
            <StatusBadge status={ticket.status} />
            {ticket.priority && <PriorityBadge priority={ticket.priority} />}
            <HITLBadge required={ticket.hitl_required} />
            {ticket.sla_escalated && <span className="badge badge-escalated">SLA escalated</span>}
          </div>

          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text)', lineHeight: 1.35, marginBottom: compact ? 0 : 5 }}>
            {ticket.title}
          </div>

          {!compact && (
            <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {ticket.description}
            </div>
          )}

          {!compact && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 10, color: 'var(--text-muted)', fontSize: 12 }}>
              {ticket.category && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                  <Bot size={13} />
                  {CATEGORY_LABELS[ticket.category]}
                </span>
              )}
              {ticket.routing_target && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: 'var(--cyan)' }}>
                  <GitBranch size={13} />
                  {ticket.routing_target}
                </span>
              )}
              <span>{formatRelative(ticket.created_at)}</span>
            </div>
          )}
        </div>

        <div className="ticket-card-meta" style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
          <SLABadge deadline={ticket.sla_deadline} />
          {!compact && <ConfidenceBadge score={ticket.confidence_score} />}
          {onApprove && ticket.status === 'pending_hitl' && (
            <button
              className="btn-primary"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onApprove(ticket);
              }}
            >
              <ShieldAlert size={15} />
              Xem duyệt
            </button>
          )}
          {linkTo && compact && <ArrowRight size={16} color="var(--text-muted)" />}
        </div>
      </div>
    </div>
  );

  if (linkTo) {
    return <Link href={linkTo} style={{ textDecoration: 'none' }}>{card}</Link>;
  }

  return card;
}
