'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, ShieldAlert } from 'lucide-react';
import HITLModal from '@/components/HITLModal';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import { Ticket } from '@/types';
import api from '@/lib/api';

export default function ApprovalsPage() {
  const [hitlTicket, setHitlTicket] = useState<Ticket | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['pending-hitl'],
    queryFn: async () => (await api.get('/tickets/pending-hitl')).data as Ticket[],
    refetchInterval: 10000,
  });

  const tickets = data ?? [];

  return (
    <div>
      <PageHeader
        title="Duyệt HITL"
        subtitle="Ticket production, VIP, security hoặc confidence thấp cần người quản lý quyết định."
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      <div className="card" style={{ padding: 14, marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <div style={{ width: 38, height: 38, borderRadius: 8, background: 'var(--amber-soft)', color: 'var(--amber)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ShieldAlert size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 800 }}>{tickets.length} ticket đang chờ quyết định</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Approve để ticket tiếp tục route/execute, reject để đưa về trạng thái mở và chờ xử lý thủ công.</div>
        </div>
      </div>

      {isLoading ? (
        <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div>
      ) : tickets.length === 0 ? (
        <div className="card">
          <EmptyState icon="check" title="Không có ticket cần phê duyệt" desc="Tất cả quyết định HITL đã được xử lý." />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 12 }}>
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} onApprove={() => setHitlTicket(ticket)} />
          ))}
        </div>
      )}

      {hitlTicket && <HITLModal ticket={hitlTicket} onClose={() => setHitlTicket(null)} />}
    </div>
  );
}
