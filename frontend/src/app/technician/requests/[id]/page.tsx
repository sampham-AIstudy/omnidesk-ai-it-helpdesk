'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, ClipboardList, LoaderCircle } from 'lucide-react';
import api from '@/lib/api';
import { formatVietnamTime } from '@/lib/utils';

type Activity = { action: string; actor_name?: string | null; description: string; created_at: string };
type Detail = {
  request_number: string; service_name: string; status: string; fulfillment_group: string;
  requester_name?: string | null; assignee_name?: string | null; form_data: string;
  created_at: string; updated_at: string; fulfilled_at?: string | null; activity: Activity[];
};
const labels: Record<string, string> = { submitted: 'Đã vào hàng chờ', assigned: 'Đã nhận', in_progress: 'Đang xử lý', waiting_for_user: 'Đang chờ người dùng', fulfilled: 'Đã hoàn tất' };

export default function TechnicianRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestNumber = params.id;
  const [request, setRequest] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api.get<Detail>(`/service-requests/${requestNumber}`)
      .then(({ data }) => { if (active) setRequest(data); })
      .catch(() => { if (active) setError('Không thể tải Service Request hoặc bạn không có quyền truy cập.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [requestNumber]);

  const mutate = async (path: string, body?: object) => {
    setPending(true); setError('');
    try { setRequest((await api.post<Detail>(path, body)).data); }
    catch (caught: unknown) {
      const response = (caught as { response?: { data?: { detail?: string } } }).response;
      setError(response?.data?.detail ?? 'Cập nhật không thành công. Trạng thái chưa được thay đổi.');
      try {
        const refreshed = await api.get<Detail>(`/service-requests/${requestNumber}`);
        setRequest(refreshed.data);
      } catch {
        // Keep the last confirmed server response visible when refresh also fails.
      }
    } finally { setPending(false); }
  };
  const submittedFields = request ? (() => { try { return Object.entries(JSON.parse(request.form_data) as Record<string, string>); } catch { return []; } })() : [];

  return <main className="mx-auto max-w-4xl space-y-6 p-6 lg:p-10">
    <Link href="/technician/requests" className="text-sm text-cyan-300 hover:text-cyan-100">← Service Request Workbench</Link>
    {loading && <div className="flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-300"><LoaderCircle className="animate-spin" size={18} />Đang tải request…</div>}
    {error && <div role="alert" className="flex items-center gap-2 rounded-2xl border border-red-400/40 bg-red-400/10 p-5 text-sm text-red-100"><AlertCircle size={18} />{error}</div>}
    {request && <><section className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><div className="flex flex-wrap items-start justify-between gap-5"><div><p className="font-mono text-xs text-cyan-300">{request.request_number}</p><h1 className="mt-1 text-2xl font-bold text-white">{request.service_name}</h1><p className="mt-2 text-sm text-slate-400">Người yêu cầu: {request.requester_name ?? '—'} · Nhóm: {request.fulfillment_group}</p></div><div className="rounded-xl bg-slate-800 px-4 py-3 text-right"><p className="font-semibold text-cyan-100">{labels[request.status] ?? request.status}</p><p className="mt-1 text-xs text-slate-400">Cập nhật {formatVietnamTime(request.updated_at)}</p></div></div>
      <div className="mt-6 flex flex-wrap gap-3">
        {request.status === 'submitted' && <button disabled={pending} onClick={() => void mutate(`/service-requests/${request.request_number}/takeover`)} className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">{pending ? 'Đang nhận…' : 'Nhận xử lý'}</button>}
        {request.status === 'assigned' && <button disabled={pending} onClick={() => void mutate(`/service-requests/${request.request_number}/transition`, { target_status: 'in_progress' })} className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">{pending ? 'Đang cập nhật…' : 'Bắt đầu xử lý'}</button>}
        {request.status === 'in_progress' && <><button disabled={pending} onClick={() => void mutate(`/service-requests/${request.request_number}/transition`, { target_status: 'waiting_for_user' })} className="rounded-xl border border-slate-500 px-4 py-2 text-sm disabled:opacity-50">Chờ người dùng</button><button disabled={pending} onClick={() => void mutate(`/service-requests/${request.request_number}/transition`, { target_status: 'fulfilled' })} className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">{pending ? 'Đang hoàn tất…' : 'Hoàn tất'}</button></>}
        {request.status === 'waiting_for_user' && <button disabled={pending} onClick={() => void mutate(`/service-requests/${request.request_number}/transition`, { target_status: 'in_progress' })} className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">Tiếp tục xử lý</button>}
      </div></section>
      <section className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><h2 className="font-semibold text-white">Thông tin đã gửi</h2><dl className="mt-4 space-y-3 text-sm">{submittedFields.map(([key, value]) => <div key={key} className="grid gap-1 border-b border-slate-800 pb-3 sm:grid-cols-[180px_1fr]"><dt className="text-slate-400">{key}</dt><dd className="whitespace-pre-wrap text-slate-100">{value}</dd></div>)}</dl><p className="mt-4 text-sm text-slate-400">Người xử lý: {request.assignee_name ?? 'Chưa có'}</p></section>
      <section className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><div className="flex items-center gap-2"><ClipboardList size={18} className="text-cyan-300" /><h2 className="font-semibold text-white">Hoạt động</h2></div><ol className="mt-4 space-y-3">{request.activity.map((entry, index) => <li key={`${entry.action}-${index}`} className="flex gap-3 text-sm"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-cyan-300" /><div><p className="text-slate-100">{entry.description}</p><p className="mt-1 text-xs text-slate-400">{entry.actor_name ?? 'Hệ thống'} · {formatVietnamTime(entry.created_at)}</p></div></li>)}</ol></section>
    </>}
  </main>;
}
