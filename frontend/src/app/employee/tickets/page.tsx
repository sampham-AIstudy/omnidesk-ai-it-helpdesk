'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { RefreshCw } from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, QueryError, Skeleton } from '@/components/ui';
import { Ticket, TicketStatus } from '@/types';
import { getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

const FILTERS: { value: TicketStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'classifying', label: 'AI đang đọc' },
  { value: 'pending_hitl', label: 'Chờ duyệt' },
  { value: 'in_progress', label: 'Đang xử lý' },
  { value: 'closed', label: 'Đã đóng' },
];

export default function MyTicketsPage() {
  const searchParams = useSearchParams();
  const [filter, setFilter] = useState<TicketStatus | 'all'>('all');
  const ticketNumberFilter = searchParams.get('ticket')?.trim().toLowerCase() || '';

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['my-tickets', filter, ticketNumberFilter],
    queryFn: async () => {
      const params = filter !== 'all' ? `&status=${filter}` : '';
      const search = ticketNumberFilter ? `&search=${encodeURIComponent(ticketNumberFilter)}` : '';
      return (await api.get(`/tickets?page=1&page_size=50${params}${search}`)).data as { items: Ticket[]; total: number };
    },
    staleTime: 30000,
    refetchOnWindowFocus: false,
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

  const tickets = data?.items ?? [];
  const visibleTickets = ticketNumberFilter
    ? tickets.filter((ticket) => ticket.ticket_number.toLowerCase().includes(ticketNumberFilter))
    : tickets;

  return (
    <div>
      <PageHeader
        title="Ticket của tôi"
        subtitle={ticketNumberFilter
          ? `Kết quả cho mã ${ticketNumberFilter.toUpperCase()}`
          : `${data?.total ?? 0} yêu cầu trong phạm vi tài khoản của bạn`}
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
        {FILTERS.map((item) => (
          <button
            key={item.value}
            onClick={() => setFilter(item.value)}
            className={filter === item.value ? 'btn-primary' : 'btn-ghost'}
            style={{ height: 32 }}
          >
            {item.label}
          </button>
        ))}
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
            title="Không có ticket"
            desc={filter === 'all' ? 'Bạn chưa tạo ticket nào.' : 'Không có ticket trong trạng thái đang chọn.'}
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
