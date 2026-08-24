'use client';

import { useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import api from '@/lib/api';
import { EmptyState, Spinner } from '@/components/ui';

export default function TicketReferencePage() {
  const params = useParams<{ ticketNumber: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const ticketNumber = decodeURIComponent(params.ticketNumber || '');
  const messageId = searchParams.get('message');
  const { data, isLoading, isError } = useQuery<{ id: number }>({
    queryKey: ['ticket-reference', ticketNumber],
    enabled: Boolean(ticketNumber),
    queryFn: async () => (await api.get(`/tickets/resolve/${encodeURIComponent(ticketNumber)}`)).data,
    retry: false,
  });

  useEffect(() => {
    if (!data?.id) return;
    const anchor = messageId ? `?message=${encodeURIComponent(messageId)}#ticket-message-${encodeURIComponent(messageId)}` : '';
    router.replace(`/employee/tickets/${data.id}${anchor}`);
  }, [data?.id, messageId, router]);

  if (isLoading || data?.id) {
    return <div className="py-16 flex justify-center"><Spinner size={28} /></div>;
  }
  if (isError) {
    return <EmptyState icon="inbox" title="Không thể mở ticket tham chiếu" desc="Ticket này không còn tồn tại hoặc bạn không có quyền xem." />;
  }
  return null;
}
