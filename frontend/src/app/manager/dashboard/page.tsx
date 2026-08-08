'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Bot, CheckCircle2, RefreshCw, ShieldAlert, Siren, Timer } from 'lucide-react';
import HITLModal from '@/components/HITLModal';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import { DashboardResponse, Ticket } from '@/types';
import api from '@/lib/api';

export default function ManagerDashboard() {
  const [hitlTicket, setHitlTicket] = useState<Ticket | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => (await api.get('/analytics/dashboard')).data as DashboardResponse,
    refetchInterval: 20000,
  });

  const { data: slaAlerts } = useQuery({
    queryKey: ['sla-alerts'],
    queryFn: async () => (await api.get('/analytics/sla-alerts')).data as Ticket[],
    refetchInterval: 30000,
  });

  if (isLoading) return <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}><Spinner size={34} /></div>;

  const cls = data?.classification;
  const sla = data?.sla;
  const pendingHitl = data?.pending_hitl ?? [];
  const recentTickets = data?.recent_tickets ?? [];
  const alerts = slaAlerts ?? [];
  const slaCompliance = Math.round((sla?.sla_compliance_rate ?? 0) * 100);
  const avgConfidence = Math.round((cls?.avg_confidence ?? 0) * 100);

  return (
    <div>
      <PageHeader
        title="Control tower IT Help Desk"
        subtitle="Giám sát agent, HITL, SLA và rủi ro vận hành theo thời gian gần thực."
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      {alerts.length > 0 && (
        <div className="card" style={{ padding: 14, marginBottom: 16, borderColor: '#ffd4d4', background: 'var(--red-soft)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <Siren size={20} color="var(--red)" />
          <div style={{ flex: 1 }}>
            <div style={{ color: 'var(--red)', fontWeight: 800 }}>{alerts.length} ticket sắp vi phạm SLA trong 1 giờ</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{alerts.slice(0, 3).map((ticket) => ticket.ticket_number).join(', ')}</div>
          </div>
        </div>
      )}

      <div className="manager-stat-grid" style={{ marginBottom: 18 }}>
        {[
          { label: 'Tổng ticket', value: cls?.total_tickets ?? 0, icon: Timer, color: 'var(--primary)' },
          { label: 'AI đã phân loại', value: cls?.auto_classified ?? 0, icon: Bot, color: 'var(--violet)' },
          { label: 'Chờ HITL', value: pendingHitl.length, icon: ShieldAlert, color: 'var(--amber)' },
          { label: 'SLA compliance', value: `${slaCompliance}%`, icon: CheckCircle2, color: slaCompliance >= 80 ? 'var(--green)' : 'var(--amber)' },
          { label: 'AI confidence', value: `${avgConfidence}%`, icon: AlertTriangle, color: avgConfidence >= 80 ? 'var(--green)' : 'var(--red)' },
        ].map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="stat-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>{metric.label}</span>
                <Icon size={17} color={metric.color} />
              </div>
              <div style={{ color: metric.color, fontSize: 25, fontWeight: 800 }}>{metric.value}</div>
            </div>
          );
        })}
      </div>

      <div className="manager-content-grid">
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 className="section-title">Ticket cần quyết định HITL</h2>
            <span className="badge badge-pending_hitl">{pendingHitl.length} pending</span>
          </div>

          {pendingHitl.length === 0 ? (
            <div className="card">
              <EmptyState icon="check" title="Không có HITL đang chờ" desc="Agent có thể tiếp tục xử lý những ticket đủ điều kiện." />
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {pendingHitl.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} onApprove={() => setHitlTicket(ticket)} />
              ))}
            </div>
          )}
        </section>

        <aside style={{ display: 'grid', gap: 14 }}>
          <div className="card" style={{ padding: 16 }}>
            <h2 className="section-title" style={{ marginBottom: 12 }}>SLA snapshot</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              <MetricRow label="Trong SLA" value={sla?.within_sla ?? 0} color="var(--green)" />
              <MetricRow label="Vi phạm SLA" value={sla?.sla_breached ?? 0} color="var(--red)" />
              <MetricRow label="Đã leo thang" value={sla?.escalated ?? 0} color="var(--amber)" />
            </div>
          </div>

          <div className="card" style={{ padding: 16 }}>
            <h2 className="section-title" style={{ marginBottom: 12 }}>Ticket gần đây</h2>
            <div style={{ display: 'grid', gap: 8 }}>
              {recentTickets.slice(0, 5).map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} compact linkTo={`/employee/tickets/${ticket.id}`} />
              ))}
              {recentTickets.length === 0 && <EmptyState icon="inbox" title="Chưa có ticket" />}
            </div>
          </div>
        </aside>
      </div>

      {hitlTicket && <HITLModal ticket={hitlTicket} onClose={() => setHitlTicket(null)} />}
    </div>
  );
}

function MetricRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{label}</span>
      <span style={{ color, fontSize: 18, fontWeight: 800 }}>{value}</span>
    </div>
  );
}
