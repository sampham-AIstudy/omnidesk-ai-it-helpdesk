'use client';

import Link from 'next/link';
import { useState, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { RefreshCw, PackageOpen, Plus, Search, AlertCircle, CheckCircle } from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, QueryError, Skeleton } from '@/components/ui';
import { Ticket } from '@/types';
import { getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

type EmployeeFilter = 'all' | 'open' | 'in_progress' | 'pending_closure' | 'pending_hitl' | 'closed';

export default function MyTicketsPage() {
  const searchParams = useSearchParams();
  const [filter, setFilter] = useState<EmployeeFilter>('all');
  const [keyword, setKeyword] = useState('');
  const ticketNumberFilter = searchParams.get('ticket')?.trim().toLowerCase() || '';

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['my-tickets'],
    queryFn: async () => {
      return (await api.get(`/tickets?page=1&page_size=100`)).data as { items: Ticket[]; total: number };
    },
    staleTime: 10000,
    refetchOnWindowFocus: true,
  });

  const { data: serviceRequestsData } = useQuery({
    queryKey: ['my-service-requests-count'],
    queryFn: async () => {
      try {
        const res = await api.get('/service-requests/mine');
        return (res.data?.items ?? []).length as number;
      } catch {
        return 0;
      }
    },
    staleTime: 30000,
  });

  const queryClient = useQueryClient();

  const handlePrefetch = (ticketId: number) => {
    queryClient.prefetchQuery({
      queryKey: ['ticket', String(ticketId)],
      queryFn: async () => (await api.get(`/tickets/${ticketId}`)).data,
      staleTime: 30000,
    });
    queryClient.prefetchQuery({
      queryKey: ['ticket-messages', String(ticketId)],
      queryFn: async () => (await api.get(`/tickets/${ticketId}/messages`)).data,
      staleTime: 15000,
    });
  };

  const allTickets = data?.items ?? [];

  // Group counts
  const counts = useMemo(() => {
    return {
      all: allTickets.length,
      open: allTickets.filter((t) => ['open', 'new', 'classifying', 'needs_clarification'].includes(t.status)).length,
      in_progress: allTickets.filter((t) => ['in_progress', 'human_active', 'waiting_for_agent', 'reopened', 'escalated'].includes(t.status)).length,
      pending_closure: allTickets.filter((t) => t.status === 'pending_closure').length,
      pending_hitl: allTickets.filter((t) => ['pending_hitl', 'security_review'].includes(t.status)).length,
      closed: allTickets.filter((t) => ['closed', 'resolved', 'rejected', 'cancelled'].includes(t.status)).length,
    };
  }, [allTickets]);

  const FILTERS: { value: EmployeeFilter; label: string; count: number }[] = [
    { value: 'all', label: 'Tất cả', count: counts.all },
    { value: 'open', label: 'Mới / AI tiếp nhận', count: counts.open },
    { value: 'in_progress', label: 'Đang xử lý', count: counts.in_progress },
    { value: 'pending_closure', label: 'Chờ đóng / Xác nhận', count: counts.pending_closure },
    { value: 'pending_hitl', label: 'Chờ duyệt', count: counts.pending_hitl },
    { value: 'closed', label: 'Đã hoàn tất / Đóng', count: counts.closed },
  ];

  const visibleTickets = useMemo(() => {
    return allTickets.filter((ticket) => {
      // 1. Status Filter
      if (filter === 'open') {
        if (!['open', 'new', 'classifying', 'needs_clarification'].includes(ticket.status)) return false;
      } else if (filter === 'in_progress') {
        if (!['in_progress', 'human_active', 'waiting_for_agent', 'reopened', 'escalated'].includes(ticket.status)) return false;
      } else if (filter === 'pending_closure') {
        if (ticket.status !== 'pending_closure') return false;
      } else if (filter === 'pending_hitl') {
        if (!['pending_hitl', 'security_review'].includes(ticket.status)) return false;
      } else if (filter === 'closed') {
        if (!['closed', 'resolved', 'rejected', 'cancelled'].includes(ticket.status)) return false;
      }

      // 2. URL Ticket Number Filter
      if (ticketNumberFilter && !ticket.ticket_number.toLowerCase().includes(ticketNumberFilter)) {
        return false;
      }

      // 3. Keyword Search
      if (keyword.trim()) {
        const kw = keyword.trim().toLowerCase();
        const match =
          ticket.ticket_number.toLowerCase().includes(kw) ||
          ticket.title.toLowerCase().includes(kw) ||
          (ticket.description || '').toLowerCase().includes(kw);
        if (!match) return false;
      }

      return true;
    });
  }, [allTickets, filter, ticketNumberFilter, keyword]);

  return (
    <div>
      <PageHeader
        title="Ticket của tôi"
        subtitle={ticketNumberFilter
          ? `Kết quả cho mã ${ticketNumberFilter.toUpperCase()}`
          : `Quản lý toàn bộ các yêu cầu & sự cố (${allTickets.length} ticket)`}
        action={
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-ghost" onClick={() => refetch()}>
              <RefreshCw size={15} />
              Làm mới
            </button>
            <Link href="/employee/new-ticket" className="btn-primary">
              <Plus size={15} />
              Tạo ticket mới
            </Link>
          </div>
        }
      />

      {/* Pending Closure Alert Banner if any */}
      {counts.pending_closure > 0 && filter !== 'pending_closure' && (
        <div
          style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 12,
            padding: '10px 16px',
            marginBottom: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 13,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#92400e' }}>
            <AlertCircle size={17} color="#d97706" />
            <span>
              Bạn có <strong>{counts.pending_closure} ticket đang chờ xác nhận hoàn tất / đóng</strong>.
            </span>
          </div>
          <button
            onClick={() => setFilter('pending_closure')}
            style={{
              background: '#fef3c7',
              color: '#b45309',
              border: '1px solid #fcd34d',
              padding: '4px 10px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Xem ngay →
          </button>
        </div>
      )}

      {/* Service Request Banner Link */}
      {(serviceRequestsData ?? 0) > 0 && (
        <div
          style={{
            background: 'linear-gradient(to right, #eff6ff, #f0fdf4)',
            border: '1px solid #bfdbfe',
            borderRadius: 12,
            padding: '10px 16px',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 13,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#1e40af' }}>
            <PackageOpen size={18} color="#2563eb" />
            <span>
              Bạn đang có <strong>{serviceRequestsData} yêu cầu dịch vụ (Service Request)</strong> từ IT Catalog.
            </span>
          </div>
          <Link
            href="/employee/requests"
            style={{
              color: '#2563eb',
              fontWeight: 700,
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            Xem Yêu Cầu Dịch Vụ →
          </Link>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: 18,
        }}
      >
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {FILTERS.map((item) => (
            <button
              key={item.value}
              onClick={() => setFilter(item.value)}
              className={filter === item.value ? 'btn-primary' : 'btn-ghost'}
              style={{
                height: 32,
                fontSize: 12,
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>{item.label}</span>
              {item.count > 0 && (
                <span
                  style={{
                    background: filter === item.value ? 'rgba(255,255,255,0.25)' : 'var(--surface-muted, #f1f5f9)',
                    color: filter === item.value ? '#ffffff' : 'var(--text-muted, #64748b)',
                    borderRadius: 10,
                    padding: '1px 6px',
                    fontSize: 10,
                    fontWeight: 800,
                  }}
                >
                  {item.count}
                </span>
              )}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', width: 260 }}>
          <Search
            size={14}
            style={{
              position: 'absolute',
              left: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            placeholder="Tìm theo mã, tiêu đề..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="input"
            style={{ paddingLeft: 30, height: 32, fontSize: 12 }}
          />
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'grid', gap: 12 }} aria-label="Đang tải ticket">
          {[0, 1, 2].map((item) => <Skeleton key={item} height={126} />)}
        </div>
      ) : isError ? (
        <QueryError message={getErrorMessage(error)} onRetry={() => refetch()} />
      ) : visibleTickets.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="inbox"
            title="Không có ticket phù hợp"
            desc={
              keyword
                ? `Không tìm thấy ticket nào khớp với "${keyword}".`
                : filter === 'all'
                ? 'Bạn chưa tạo ticket nào.'
                : 'Không có ticket trong bộ lọc đang chọn.'
            }
            action={<Link href="/employee/new-ticket" className="btn-primary">Gửi ticket mới</Link>}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {visibleTickets.map((ticket) => (
            <div key={ticket.id} onMouseEnter={() => handlePrefetch(ticket.id)}>
              <TicketCard ticket={ticket} linkTo={`/employee/tickets/${ticket.id}`} showSla={false} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
