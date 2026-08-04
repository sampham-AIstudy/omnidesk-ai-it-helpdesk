'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { CheckCircle2, ExternalLink, RefreshCw, Siren, Wrench } from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import { ConfidenceBadge, EmptyState, PageHeader, PriorityBadge, SLABadge, Spinner, StatusBadge } from '@/components/ui';
import { Ticket, TicketStatus } from '@/types';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

const FILTERS: { value: TicketStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'open', label: 'Mới' },
  { value: 'classifying', label: 'AI đang đọc' },
  { value: 'pending_hitl', label: 'Chờ HITL' },
  { value: 'in_progress', label: 'Đang xử lý' },
  { value: 'escalated', label: 'Leo thang' },
];

export default function TechQueuePage() {
  const [filter, setFilter] = useState<TicketStatus | 'all'>('all');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tech-queue', filter],
    queryFn: async () => {
      const params = filter !== 'all' ? `&status=${filter}` : '';
      return (await api.get(`/tickets?page=1&page_size=60${params}`)).data as { items: Ticket[]; total: number };
    },
    refetchInterval: 12000,
  });

  const tickets = useMemo(() => data?.items ?? [], [data]);
  const defaultSelected = selectedId ?? tickets[0]?.id ?? null;

  const { data: selectedTicket } = useQuery({
    queryKey: ['ticket', defaultSelected],
    queryFn: async () => (await api.get(`/tickets/${defaultSelected}`)).data as Ticket,
    enabled: !!defaultSelected,
    refetchInterval: 6000,
  });

  const closeMutation = useMutation({
    mutationFn: async (ticketId: number) => (await api.patch(`/tickets/${ticketId}/status`, { status: 'closed', note: 'Kỹ thuật viên xác nhận đã xử lý.' })).data,
    onSuccess: () => {
      toast.success('Ticket đã đóng');
      queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const escalateMutation = useMutation({
    mutationFn: async (ticketId: number) => (await api.post(`/tickets/${ticketId}/escalate`)).data,
    onSuccess: () => {
      toast.success('Ticket đã leo thang');
      queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const counts = useMemo(() => ({
    urgent: tickets.filter((ticket) => ticket.priority === 'critical' || ticket.sla_escalated).length,
    hitl: tickets.filter((ticket) => ticket.status === 'pending_hitl').length,
    lowConfidence: tickets.filter((ticket) => (ticket.confidence_score ?? 1) < 0.6).length,
  }), [tickets]);

  let ragSources: string[] = [];
  try {
    ragSources = JSON.parse(selectedTicket?.rag_sources ?? '[]');
  } catch {
    ragSources = [];
  }

  return (
    <div>
      <PageHeader
        title="Workbench kỹ thuật viên"
        subtitle={`${data?.total ?? 0} ticket trong hàng đợi theo quyền công ty/phòng ban`}
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      <div className="responsive-grid-2" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'Khẩn cấp / escalated', value: counts.urgent, color: 'var(--red)' },
          { label: 'Chờ HITL', value: counts.hitl, color: 'var(--amber)' },
          { label: 'Confidence thấp', value: counts.lowConfidence, color: 'var(--violet)' },
        ].map((item) => (
          <div key={item.label} className="stat-card">
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 8 }}>{item.label}</div>
            <div style={{ color: item.color, fontSize: 26, fontWeight: 800 }}>{item.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {FILTERS.map((item) => (
          <button key={item.value} className={filter === item.value ? 'btn-primary' : 'btn-ghost'} style={{ height: 32 }} onClick={() => setFilter(item.value)}>
            {item.label}
          </button>
        ))}
      </div>

      <div className="workbench-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          {isLoading ? (
            <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div>
          ) : tickets.length === 0 ? (
            <div className="card">
              <EmptyState icon="check" title="Hàng đợi trống" desc="Không có ticket cần xử lý với bộ lọc hiện tại." />
            </div>
          ) : (
            tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                selected={selectedTicket?.id === ticket.id}
                onClick={() => setSelectedId(ticket.id)}
              />
            ))
          )}
        </div>

        <aside className="card" style={{ padding: 16, position: 'sticky', top: 24 }}>
          {!selectedTicket ? (
            <EmptyState icon="inbox" title="Chọn một ticket" desc="Thông tin phân loại, RAG và hành động xử lý sẽ hiện ở đây." />
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800 }}>{selectedTicket.ticket_number}</div>
                  <h2 style={{ margin: '4px 0 8px', fontSize: 17, fontWeight: 800, lineHeight: 1.3 }}>{selectedTicket.title}</h2>
                  <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
                    <StatusBadge status={selectedTicket.status} />
                    {selectedTicket.priority && <PriorityBadge priority={selectedTicket.priority} />}
                  </div>
                </div>
                <a className="btn-ghost" href={`/employee/tickets/${selectedTicket.id}`} style={{ width: 36, padding: 0 }}>
                  <ExternalLink size={15} />
                </a>
              </div>

              <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.65, margin: 0 }}>{selectedTicket.description}</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>SLA</div>
                  <SLABadge deadline={selectedTicket.sla_deadline} />
                </div>
                <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 6 }}>Confidence</div>
                  <ConfidenceBadge score={selectedTicket.confidence_score} />
                </div>
              </div>

              <div className="card" style={{ padding: 12, boxShadow: 'none' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, marginBottom: 7 }}>Định tuyến</div>
                <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 800 }}>{selectedTicket.routing_target ?? 'Chưa định tuyến'}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>
                  {selectedTicket.category ? CATEGORY_LABELS[selectedTicket.category] : 'Chưa phân loại'} · {formatRelative(selectedTicket.created_at)}
                </div>
              </div>

              {selectedTicket.suggested_solution && (
                <div className="card" style={{ padding: 12, boxShadow: 'none', borderColor: '#b7e8f2' }}>
                  <div style={{ color: 'var(--cyan)', fontSize: 11, fontWeight: 800, marginBottom: 7 }}>RAG đề xuất</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>{selectedTicket.suggested_solution}</div>
                  {ragSources.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 9 }}>
                      {ragSources.slice(0, 3).map((source) => <span key={source} className="badge badge-in_progress">{source}</span>)}
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 9 }}>
                <button
                  className="btn-success"
                  disabled={closeMutation.isPending || !['open', 'in_progress'].includes(selectedTicket.status)}
                  onClick={() => closeMutation.mutate(selectedTicket.id)}
                >
                  {closeMutation.isPending ? <Spinner size={15} /> : <CheckCircle2 size={15} />}
                  Đóng
                </button>
                <button
                  className="btn-danger"
                  disabled={escalateMutation.isPending || selectedTicket.status === 'closed'}
                  onClick={() => escalateMutation.mutate(selectedTicket.id)}
                >
                  {escalateMutation.isPending ? <Spinner size={15} /> : <Siren size={15} />}
                  Leo thang
                </button>
              </div>

              <div style={{ color: 'var(--text-muted)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Wrench size={13} />
                Production/VIP/security phải qua HITL trước thao tác tự động.
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
