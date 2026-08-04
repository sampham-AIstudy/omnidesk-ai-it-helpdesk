'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Clock3, FilePlus2, Inbox, ShieldCheck } from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import { useAuthStore } from '@/lib/authStore';
import { Ticket } from '@/types';
import api from '@/lib/api';

export default function EmployeeDashboard() {
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ['my-tickets'],
    queryFn: async () => (await api.get('/tickets?page=1&page_size=12')).data as { items: Ticket[]; total: number },
    refetchInterval: 10000,
  });

  const tickets = data?.items ?? [];
  const active = tickets.filter((ticket) => ['open', 'classifying', 'in_progress'].includes(ticket.status)).length;
  const pendingHitl = tickets.filter((ticket) => ticket.status === 'pending_hitl').length;
  const done = tickets.filter((ticket) => ['resolved', 'closed'].includes(ticket.status)).length;
  const risk = tickets.filter((ticket) => ticket.sla_escalated || ticket.is_production_impact).length;

  return (
    <div>
      <PageHeader
        title={`Xin chào${user?.full_name ? `, ${user.full_name.split(' ').slice(-1)[0]}` : ''}`}
        subtitle="Gửi yêu cầu IT, theo dõi AI phân loại, HITL và SLA ở một nơi."
        action={
          <Link href="/employee/new-ticket" className="btn-primary">
            <FilePlus2 size={16} />
            Gửi ticket
          </Link>
        }
      />

      <div className="dashboard-hero-grid" style={{ gridTemplateColumns: '1.2fr 0.8fr', marginBottom: 18 }}>
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 800, marginBottom: 6 }}>Luồng xử lý ticket</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                {['Tiếp nhận', 'AI phân loại', 'RAG gợi ý', 'HITL nếu cần', 'Định tuyến / đóng'].map((step, index) => (
                  <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ height: 26, padding: '0 10px', borderRadius: 999, background: index === 0 ? 'var(--primary-soft)' : 'var(--surface-muted)', color: index === 0 ? 'var(--primary)' : 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', fontSize: 12, fontWeight: 800 }}>
                      {step}
                    </span>
                    {index < 4 && <span style={{ color: 'var(--border-strong)', fontWeight: 800 }}>→</span>}
                  </div>
                ))}
              </div>
            </div>
            {user?.is_vip && (
              <div className="badge badge-medium">
                <ShieldCheck size={12} />
                VIP: luôn có HITL
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: 18, borderColor: risk > 0 ? '#ffd4d4' : 'var(--border)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ width: 38, height: 38, borderRadius: 8, background: risk > 0 ? 'var(--red-soft)' : 'var(--green-soft)', color: risk > 0 ? 'var(--red)' : 'var(--green)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {risk > 0 ? <AlertTriangle size={19} /> : <CheckCircle2 size={19} />}
            </div>
            <div>
              <div style={{ fontWeight: 800 }}>{risk > 0 ? `${risk} ticket cần chú ý` : 'Không có cảnh báo'}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>SLA leo thang hoặc ảnh hưởng production sẽ được ưu tiên.</div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-stat-grid" style={{ marginBottom: 22 }}>
        {[
          { label: 'Tổng ticket', value: data?.total ?? 0, icon: Inbox, color: 'var(--primary)' },
          { label: 'Đang xử lý', value: active, icon: Clock3, color: 'var(--cyan)' },
          { label: 'Chờ HITL', value: pendingHitl, icon: ShieldCheck, color: 'var(--amber)' },
          { label: 'Hoàn tất', value: done, icon: CheckCircle2, color: 'var(--green)' },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="stat-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>{stat.label}</span>
                <Icon size={18} color={stat.color} />
              </div>
              <div style={{ color: stat.color, fontSize: 30, fontWeight: 800 }}>{stat.value}</div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 className="section-title">Ticket gần đây</h2>
        <Link href="/employee/tickets" style={{ color: 'var(--primary)', fontSize: 13, fontWeight: 800, textDecoration: 'none' }}>Xem tất cả</Link>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : tickets.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="inbox"
            title="Bạn chưa có ticket"
            desc="Gửi yêu cầu đầu tiên để agent phân loại, tìm KB và định tuyến tự động."
            action={<Link href="/employee/new-ticket" className="btn-primary">Gửi ticket</Link>}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {tickets.slice(0, 6).map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} linkTo={`/employee/tickets/${ticket.id}`} />
          ))}
        </div>
      )}
    </div>
  );
}
