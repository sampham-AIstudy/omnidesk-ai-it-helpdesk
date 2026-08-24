'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, ShieldAlert, ClipboardCheck } from 'lucide-react';
import HITLModal from '@/components/HITLModal';
import TicketCard from '@/components/TicketCard';
import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import { Ticket } from '@/types';
import { formatVietnamTime } from '@/lib/utils';
import api from '@/lib/api';

type ServiceRequestApproval = {
  request_number: string; service_name: string; requester_name?: string | null;
  fulfillment_group: string; form_data: string; created_at: string; status: string;
};

function errorDetail(error: unknown) {
  return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Không thể lưu quyết định. Dữ liệu máy chủ chưa thay đổi.';
}

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'incident' | 'service-request'>('incident');
  const [hitlTicket, setHitlTicket] = useState<Ticket | null>(null);
  const [rejecting, setRejecting] = useState<ServiceRequestApproval | null>(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const hitl = useQuery({ queryKey: ['pending-hitl'], queryFn: async () => (await api.get('/tickets/pending-hitl')).data as Ticket[], refetchInterval: 10000 });
  const approvals = useQuery({ queryKey: ['pending-service-request-approvals'], queryFn: async () => (await api.get<{ items: ServiceRequestApproval[] }>('/service-requests/pending-approval')).data.items });
  const decide = useMutation({
    mutationFn: async ({ requestNumber, decision, body }: { requestNumber: string; decision: 'approve' | 'reject'; body: object }) => api.post(`/service-requests/${requestNumber}/${decision}`, body),
    onSuccess: () => { setError(''); setRejecting(null); setReason(''); void queryClient.invalidateQueries({ queryKey: ['pending-service-request-approvals'] }); },
    onError: (caught) => { setError(errorDetail(caught)); void queryClient.invalidateQueries({ queryKey: ['pending-service-request-approvals'] }); },
  });
  const tickets = hitl.data ?? [];
  const requests = approvals.data ?? [];

  return <div>
    <PageHeader title="Phê duyệt" subtitle="Incident HITL và Service Request cần phê duyệt được tách thành hai luồng quyết định." action={<button className="btn-ghost" onClick={() => { void hitl.refetch(); void approvals.refetch(); }}><RefreshCw size={15} />Làm mới</button>} />
    <div className="mb-4 flex gap-2"><button type="button" className={tab === 'incident' ? 'btn-primary' : 'btn-ghost'} onClick={() => setTab('incident')}>Incident HITL ({tickets.length})</button><button type="button" className={tab === 'service-request' ? 'btn-primary' : 'btn-ghost'} onClick={() => setTab('service-request')}>Service Requests ({requests.length})</button></div>
    {error && <div role="alert" className="mb-4 rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
    {tab === 'incident' && <><div className="card" style={{ padding: 14, marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}><div style={{ width: 38, height: 38, borderRadius: 8, background: 'var(--amber-soft)', color: 'var(--amber)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><ShieldAlert size={20} /></div><div><div style={{ fontWeight: 800 }}>{tickets.length} ticket đang chờ quyết định</div><div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Incident HITL giữ nguyên semantics hiện có.</div></div></div>{hitl.isLoading ? <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div> : tickets.length === 0 ? <div className="card"><EmptyState icon="check" title="Không có ticket cần phê duyệt" desc="Tất cả quyết định HITL đã được xử lý." /></div> : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 12 }}>{tickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} onApprove={() => setHitlTicket(ticket)} />)}</div>}</>}
    {tab === 'service-request' && <><div className="card" style={{ padding: 14, marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}><div style={{ width: 38, height: 38, borderRadius: 8, background: 'var(--blue-soft)', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><ClipboardCheck size={20} /></div><div><div style={{ fontWeight: 800 }}>{requests.length} Service Request chờ phê duyệt</div><div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Phê duyệt chỉ đưa request vào fulfillment queue; không hoàn tất dịch vụ.</div></div></div>{approvals.isLoading ? <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div> : requests.length === 0 ? <div className="card"><EmptyState icon="check" title="Không có Service Request chờ phê duyệt" desc="Các request đã quyết định sẽ không còn trong hàng chờ này." /></div> : <div className="grid gap-3">{requests.map((request) => <section key={request.request_number} className="card p-5"><div className="flex flex-wrap justify-between gap-4"><div><p className="font-mono text-xs text-blue-400">{request.request_number}</p><h2 className="mt-1 font-semibold">{request.service_name}</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Người yêu cầu: {request.requester_name ?? '—'} · Nhóm: {request.fulfillment_group}</p><p className="mt-1 text-xs text-[var(--text-muted)]">Gửi lúc {formatVietnamTime(request.created_at)}</p></div><div className="flex h-fit gap-2"><button type="button" className="btn-primary" disabled={decide.isPending} onClick={() => decide.mutate({ requestNumber: request.request_number, decision: 'approve', body: {} })}>{decide.isPending ? 'Đang xử lý…' : 'Phê duyệt'}</button><button type="button" className="btn-ghost" disabled={decide.isPending} onClick={() => { setError(''); setRejecting(request); }}>Từ chối</button></div></div></section>)}</div>}</>}
    {hitlTicket && <HITLModal ticket={hitlTicket} onClose={() => setHitlTicket(null)} />}
    {rejecting && <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4"><section role="dialog" aria-modal="true" className="glass-card w-full max-w-lg p-6"><h2 className="text-lg font-semibold">Từ chối {rejecting.request_number}</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Lý do sẽ được gửi lại cho người yêu cầu.</p><textarea className="mt-4 min-h-28 w-full rounded border p-3" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Nhập lý do từ chối (ít nhất 3 ký tự)" /><div className="mt-5 flex justify-end gap-3"><button type="button" className="btn-ghost" disabled={decide.isPending} onClick={() => setRejecting(null)}>Hủy</button><button type="button" className="btn-primary" disabled={decide.isPending || reason.trim().length < 3} onClick={() => decide.mutate({ requestNumber: rejecting.request_number, decision: 'reject', body: { reason: reason.trim() } })}>{decide.isPending ? 'Đang xử lý…' : 'Xác nhận từ chối'}</button></div></section></div>}
  </div>;
}
