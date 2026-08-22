'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Inbox,
  RefreshCw,
  ShieldAlert,
  Siren,
  Timer,
  Zap,
} from 'lucide-react';
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

  if (isLoading)
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
        <Spinner size={34} />
      </div>
    );

  const cls = data?.classification;
  const sla = data?.sla;
  const pendingHitl = data?.pending_hitl ?? [];
  const alerts = slaAlerts ?? [];
  const slaCompliance = Math.round((sla?.sla_compliance_rate ?? 0) * 100);
  const avgConfidence = Math.round((cls?.avg_confidence ?? 0) * 100);

  return (
    <div>
      <PageHeader
        title="Control Tower IT Help Desk"
        subtitle="Trung tâm chỉ huy & Radar rủi ro SLA, các điểm nghẽn HITL và chỉ số vận hành."
        action={
          <div style={{ display: 'flex', gap: 10 }}>
            <Link href="/manager/tickets" className="btn-primary" style={{ textDecoration: 'none' }}>
              <Inbox size={15} /> Hàng đợi sự cố
            </Link>
            <button className="btn-ghost" onClick={() => refetch()}>
              <RefreshCw size={15} /> Làm mới
            </button>
          </div>
        }
      />

      {alerts.length > 0 && (
        <div
          className="card"
          style={{
            padding: 14,
            marginBottom: 16,
            borderColor: '#ffd4d4',
            background: 'var(--red-soft)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <Siren size={20} color="var(--red)" />
          <div style={{ flex: 1 }}>
            <div style={{ color: 'var(--red)', fontWeight: 800 }}>
              🚨 {alerts.length} sự cố sắp vi phạm SLA trong vòng 1 giờ
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
              {alerts.slice(0, 4).map((ticket) => ticket.ticket_number).join(', ')}
            </div>
          </div>
        </div>
      )}

      {/* High-level KPI Radar */}
      <div className="manager-stat-grid" style={{ marginBottom: 18 }}>
        {[
          { label: 'Tổng sự cố', value: cls?.total_tickets ?? 0, icon: Timer, color: 'var(--primary)' },
          { label: 'AI đã phân loại', value: cls?.auto_classified ?? 0, icon: Bot, color: 'var(--violet)' },
          { label: 'Chờ duyệt HITL', value: pendingHitl.length, icon: ShieldAlert, color: 'var(--amber)' },
          {
            label: 'SLA compliance',
            value: `${slaCompliance}%`,
            icon: CheckCircle2,
            color: slaCompliance >= 80 ? 'var(--green)' : 'var(--amber)',
          },
          {
            label: 'Độ tin cậy AI',
            value: `${avgConfidence}%`,
            icon: AlertTriangle,
            color: avgConfidence >= 80 ? 'var(--green)' : 'var(--red)',
          },
        ].map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="stat-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>
                  {metric.label}
                </span>
                <Icon size={17} color={metric.color} />
              </div>
              <div style={{ color: metric.color, fontSize: 25, fontWeight: 800 }}>{metric.value}</div>
            </div>
          );
        })}
      </div>

      <div className="manager-content-grid">
        {/* Left: Urgent HITL Blockers */}
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 className="section-title">Điểm nghẽn cần Quản lý duyệt (HITL Gate)</h2>
            <span className="badge badge-pending_hitl">{pendingHitl.length} sự cố</span>
          </div>

          {pendingHitl.length === 0 ? (
            <div className="card">
              <EmptyState
                icon="check"
                title="Không có điểm nghẽn HITL"
                desc="Tất cả các hành động tự động hóa của AI đang vận hành trơn tru."
              />
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {pendingHitl.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} onApprove={() => setHitlTicket(ticket)} />
              ))}
            </div>
          )}
        </section>

        {/* Right: SLA Risk Radar & Operational CTA */}
        <aside style={{ display: 'grid', gap: 14 }}>
          {/* SLA Health */}
          <div className="card" style={{ padding: 16 }}>
            <h2 className="section-title" style={{ marginBottom: 12 }}>SLA Health Radar</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              <MetricRow label="Trong hạn cam kết" value={sla?.within_sla ?? 0} color="var(--green)" />
              <MetricRow label="Đã vi phạm SLA" value={sla?.sla_breached ?? 0} color="var(--red)" />
              <MetricRow label="Đã leo thang cấp quản lý" value={sla?.escalated ?? 0} color="var(--amber)" />
            </div>
          </div>

          {/* Quick CTA to Full Triage Queue */}
          <div
            className="card"
            style={{
              padding: 16,
              background: 'linear-gradient(135deg, var(--surface-soft, #f8fafc), var(--surface, #ffffff))',
              border: '1px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <Zap size={18} color="var(--primary)" />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 800 }}>Bàn tác chiến & Hàng đợi sự cố</h3>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, margin: '0 0 14px' }}>
              Truy cập hàng đợi đầy đủ để tìm kiếm từ khóa, phân công chuyên viên, và tham gia chỉ đạo cuộc trao đổi.
            </p>
            <Link
              href="/manager/tickets"
              className="btn-primary"
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 8,
                textDecoration: 'none',
              }}
            >
              Mở Hàng đợi sự cố <ArrowRight size={15} />
            </Link>
          </div>
        </aside>
      </div>

      {hitlTicket && <HITLModal ticket={hitlTicket} onClose={() => setHitlTicket(null)} />}
    </div>
  );
}

function MetricRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '9px 0',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{label}</span>
      <span style={{ color, fontSize: 18, fontWeight: 800 }}>{value}</span>
    </div>
  );
}
