'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { CheckCircle2, Database, ShieldAlert, X, XCircle } from 'lucide-react';
import { ConfidenceBadge, PriorityBadge, Spinner } from './ui';
import { Ticket } from '@/types';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

interface Props {
  ticket: Ticket;
  onClose: () => void;
}

export default function HITLModal({ ticket, onClose }: Props) {
  const [note, setNote] = useState('');
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);
  const queryClient = useQueryClient();

  const decisionMutation = useMutation({
    mutationFn: async (approved: boolean) => (await api.post(`/tickets/${ticket.id}/approve`, { approved, note: note || null })).data,
    onSuccess: (_, approved) => {
      toast.success(approved ? 'Đã phê duyệt ticket' : 'Đã từ chối HITL');
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['pending-hitl'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      onClose();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  let ragSources: string[] = [];
  try {
    ragSources = JSON.parse(ticket.rag_sources ?? '[]');
  } catch {
    ragSources = [];
  }

  return (
    <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-box">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, marginBottom: 18 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ width: 42, height: 42, borderRadius: 8, background: 'var(--amber-soft)', color: 'var(--amber)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldAlert size={22} />
            </div>
            <div>
              <div style={{ color: 'var(--amber)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>Human-in-the-loop</div>
              <h2 style={{ margin: '2px 0 4px', fontSize: 18, fontWeight: 800 }}>{ticket.ticket_number}</h2>
              <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{ticket.title}</div>
            </div>
          </div>
          <button className="btn-ghost" style={{ width: 34, padding: 0 }} onClick={onClose}><X size={16} /></button>
        </div>

        <div className="card" style={{ padding: 14, boxShadow: 'none', marginBottom: 14 }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 8 }}>Mô tả ticket</div>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.65 }}>{ticket.description}</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
          <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Category</div>
            <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 800 }}>{ticket.category ? CATEGORY_LABELS[ticket.category] : 'Chưa có'}</div>
          </div>
          <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Priority</div>
            {ticket.priority ? <PriorityBadge priority={ticket.priority} /> : <span className="muted" style={{ fontSize: 12 }}>Chưa có</span>}
          </div>
          <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Confidence</div>
            <ConfidenceBadge score={ticket.confidence_score} />
          </div>
        </div>

        {ticket.agent_reasoning && (
          <div className="card" style={{ padding: 14, boxShadow: 'none', marginBottom: 14 }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 8 }}>Lý do agent yêu cầu kiểm soát</div>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6 }}>{ticket.agent_reasoning}</p>
          </div>
        )}

        {ticket.suggested_solution && (
          <div className="card" style={{ padding: 14, boxShadow: 'none', marginBottom: 14, borderColor: '#b7e8f2' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--cyan)', fontSize: 11, fontWeight: 800, marginBottom: 8 }}>
              <Database size={14} />
              RAG đề xuất
            </div>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{ticket.suggested_solution}</p>
            {ragSources.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                {ragSources.map((source) => <span key={source} className="badge badge-in_progress">{source}</span>)}
              </div>
            )}
          </div>
        )}

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', color: 'var(--text)', fontSize: 13, fontWeight: 800, marginBottom: 7 }}>Ghi chú quyết định</label>
          <textarea
            className="input-field"
            rows={3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Ví dụ: Duyệt định tuyến vì không thao tác trực tiếp production, yêu cầu team kiểm tra log trước..."
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <button
            className="btn-success"
            disabled={decisionMutation.isPending}
            onClick={() => {
              setDecision('approve');
              decisionMutation.mutate(true);
            }}
            style={{ height: 42 }}
          >
            {decisionMutation.isPending && decision === 'approve' ? <Spinner size={16} /> : <CheckCircle2 size={16} />}
            Phê duyệt
          </button>
          <button
            className="btn-danger"
            disabled={decisionMutation.isPending}
            onClick={() => {
              setDecision('reject');
              decisionMutation.mutate(false);
            }}
            style={{ height: 42 }}
          >
            {decisionMutation.isPending && decision === 'reject' ? <Spinner size={16} /> : <XCircle size={16} />}
            Từ chối
          </button>
        </div>

        <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 12 }}>
          Tạo lúc {formatRelative(ticket.created_at)} · Mọi quyết định sẽ được ghi audit log.
        </div>
      </div>
    </div>
  );
}
