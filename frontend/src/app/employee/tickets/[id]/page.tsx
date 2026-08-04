'use client';

import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Bot, CheckCircle2, Database, History, ShieldAlert, Split, TriangleAlert, XCircle } from 'lucide-react';
import { ConfidenceBadge, EmptyState, HITLBadge, PageHeader, PriorityBadge, SLABadge, Spinner, StatusBadge } from '@/components/ui';
import { AuditLog, Ticket } from '@/types';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: ticket, isLoading, refetch } = useQuery({
    queryKey: ['ticket', id],
    queryFn: async () => (await api.get(`/tickets/${id}`)).data as Ticket,
    refetchInterval: 8000,
  });

  const { data: auditData } = useQuery({
    queryKey: ['audit', id],
    queryFn: async () => (await api.get(`/analytics/audit-logs?ticket_id=${id}&page_size=30`)).data,
    enabled: !!ticket,
  });

  const confirmMutation = useMutation({
    mutationFn: async (resolved: boolean) =>
      (await api.post(`/tickets/${id}/confirm-resolution?resolved=${resolved}`)).data,
    onSuccess: (_, resolved) => {
      if (resolved) {
        toast.success('Cảm ơn bạn! Ticket đã được cập nhật thành Đã xử lý.');
      } else {
        toast.success('Đã gửi ticket đến cho phòng ban phụ trách.');
      }
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      queryClient.invalidateQueries({ queryKey: ['my-tickets'] });
      refetch();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  if (isLoading) return <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}><Spinner size={34} /></div>;
  if (!ticket) return <EmptyState icon="warning" title="Không tìm thấy ticket" />;

  const auditLogs: AuditLog[] = auditData?.items ?? [];
  let ragSources: string[] = [];
  try {
    ragSources = JSON.parse(ticket.rag_sources ?? '[]');
  } catch {
    ragSources = [];
  }

  return (
    <div>
      <PageHeader
        title={ticket.title}
        subtitle={`${ticket.ticket_number} · ${formatRelative(ticket.created_at)}`}
        action={<StatusBadge status={ticket.status} />}
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 330px', gap: 18, alignItems: 'start' }}>
        <div style={{ display: 'grid', gap: 14 }}>
          {ticket.status === 'classifying' && (
            <div className="card" style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 12, borderColor: '#dccbff' }}>
              <Spinner size={20} />
              <div>
                <div style={{ color: 'var(--violet)', fontWeight: 800 }}>Agent đang xử lý</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Classifier → RAG → HITL → Router</div>
              </div>
            </div>
          )}

          {ticket.is_production_impact && (
            <div className="card" style={{ padding: 14, borderColor: '#ffd4d4', background: 'var(--red-soft)', display: 'flex', gap: 10 }}>
              <TriangleAlert size={18} color="var(--red)" />
              <div style={{ color: 'var(--red)', fontSize: 13, fontWeight: 800 }}>Ticket ảnh hưởng production, cần kiểm soát HITL trước thao tác rủi ro.</div>
            </div>
          )}

          <div className="card" style={{ padding: 18 }}>
            <h2 className="section-title" style={{ marginBottom: 10 }}>Mô tả vấn đề</h2>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{ticket.description}</p>
          </div>

          {ticket.agent_reasoning && (
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <Bot size={17} color="var(--primary)" />
                <h2 className="section-title">Phân tích của agent</h2>
              </div>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.65 }}>{ticket.agent_reasoning}</p>
            </div>
          )}

          {ticket.suggested_solution && (
            <div className="card" style={{ padding: 18, borderColor: '#b7e8f2' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <Database size={17} color="var(--cyan)" />
                <h2 className="section-title">Gợi ý giải pháp từ knowledge base</h2>
              </div>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{ticket.suggested_solution}</p>
              {ragSources.length > 0 && (
                <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 12 }}>
                  {ragSources.map((source) => (
                    <span key={source} className="badge badge-in_progress">{source}</span>
                  ))}
                </div>
              )}

              {/* Ngưỡng 1: Confidence > 85% */}
              {(ticket.confidence_score ?? 0) >= 0.85 && (ticket.status === 'closed' || ticket.status === 'resolved') && (
                <div style={{ marginTop: 14, padding: 12, borderRadius: 8, background: 'var(--green-soft)', border: '1px solid #bce7d2', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CheckCircle2 size={18} color="var(--green)" />
                  <div style={{ fontSize: 13, color: 'var(--green)', fontWeight: 700 }}>
                    Giải pháp có độ tin cậy cao ({((ticket.confidence_score ?? 0) * 100).toFixed(0)}%). Ticket đã tự động đóng thành công!
                  </div>
                </div>
              )}

              {/* Ngưỡng 2: Confidence 70% - 85% */}
              {(ticket.confidence_score ?? 0) >= 0.70 && (ticket.confidence_score ?? 0) < 0.85 && ticket.status !== 'closed' && ticket.status !== 'resolved' && (
                <div style={{ marginTop: 14, padding: 14, borderRadius: 8, background: 'var(--amber-soft)', border: '1px solid #ffe0b2' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--amber)', fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                    <TriangleAlert size={16} />
                    Không chắc chắn phương pháp này thành công (Độ tin cậy: {((ticket.confidence_score ?? 0) * 100).toFixed(0)}%)
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Vui lòng thử áp dụng hướng dẫn trên và xác nhận xem vấn đề của bạn đã được giải quyết chưa:
                  </div>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      className="btn-success"
                      disabled={confirmMutation.isPending}
                      onClick={() => confirmMutation.mutate(true)}
                    >
                      <CheckCircle2 size={15} />
                      Đã giải quyết
                    </button>
                    <button
                      className="btn-danger"
                      disabled={confirmMutation.isPending}
                      onClick={() => confirmMutation.mutate(false)}
                    >
                      <XCircle size={15} />
                      Chưa giải quyết
                    </button>
                  </div>
                </div>
              )}

              {/* Ngưỡng 3: Confidence < 70% */}
              {(ticket.confidence_score ?? 1) < 0.70 && (
                <div style={{ marginTop: 14, padding: 12, borderRadius: 8, background: 'var(--violet-soft)', border: '1px solid #dccbff', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <TriangleAlert size={18} color="var(--violet)" />
                  <div style={{ fontSize: 13, color: 'var(--violet)', fontWeight: 700 }}>
                    Giải pháp có độ tin cậy không cao ({((ticket.confidence_score ?? 0) * 100).toFixed(0)}%). Đã gửi ticket đến cho phòng ban phụ trách ({ticket.routing_target || 'Kỹ thuật'}).
                  </div>
                </div>
              )}
            </div>
          )}

          {ticket.hitl_decided_at && (
            <div className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <ShieldAlert size={17} color="var(--amber)" />
                <h2 className="section-title">Quyết định HITL</h2>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                {ticket.hitl_note || 'Manager đã duyệt luồng xử lý.'}
                <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 5 }}>{formatRelative(ticket.hitl_decided_at)}</div>
              </div>
            </div>
          )}

          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <History size={17} color="var(--text-muted)" />
              <h2 className="section-title">Audit log</h2>
            </div>
            {auditLogs.length === 0 ? (
              <EmptyState icon="inbox" title="Chưa có log" />
            ) : (
              <div style={{ display: 'grid', gap: 0 }}>
                {auditLogs.map((log) => (
                  <div key={log.id} style={{ padding: '10px 0 10px 16px', borderLeft: '2px solid var(--border)', position: 'relative' }}>
                    <div style={{ position: 'absolute', left: -5, top: 15, width: 8, height: 8, borderRadius: 999, background: log.actor_type === 'agent' ? 'var(--primary)' : 'var(--border-strong)' }} />
                    <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 700 }}>{log.description}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 3 }}>{log.actor_type} · {log.model_used ?? 'system'} · {formatRelative(log.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="card" style={{ padding: 16, position: 'sticky', top: 24 }}>
          <div style={{ display: 'grid', gap: 14 }}>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Trạng thái</div>
              <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
                <StatusBadge status={ticket.status} />
                <HITLBadge required={ticket.hitl_required} />
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Phân loại</div>
              <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 700 }}>{ticket.category ? CATEGORY_LABELS[ticket.category] : 'Chưa có'}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Priority</div>
              {ticket.priority ? <PriorityBadge priority={ticket.priority} /> : <span className="muted" style={{ fontSize: 12 }}>Chưa có</span>}
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>SLA</div>
              <SLABadge deadline={ticket.sla_deadline} />
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Độ tin cậy AI</div>
              <ConfidenceBadge score={ticket.confidence_score} />
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Nhóm xử lý</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--text)', fontSize: 13, fontWeight: 700 }}>
                <Split size={14} color="var(--cyan)" />
                {ticket.routing_target ?? 'Chưa định tuyến'}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

