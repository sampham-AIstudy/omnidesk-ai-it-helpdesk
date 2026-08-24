'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AlertCircle, ClipboardList, LoaderCircle, PackageOpen } from 'lucide-react';
import api from '@/lib/api';
import { formatVietnamTime } from '@/lib/utils';

type ServiceRequest = {
  request_number: string;
  service_name: string;
  status: string;
  fulfillment_group: string;
  created_at: string;
  assignee_name?: string | null;
};

const statusLabel: Record<string, string> = {
  submitted: 'Đã vào hàng chờ', assigned: 'Đã nhận', in_progress: 'Đang xử lý',
  waiting_for_user: 'Đang chờ người dùng', fulfilled: 'Đã hoàn tất',
};

export default function TechnicianRequestsPage() {
  const [items, setItems] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.get<{ items: ServiceRequest[] }>('/service-requests/technician/queue')
      .then(({ data }) => { if (active) setItems(data.items); })
      .catch(() => { if (active) setError('Không thể tải hàng chờ Service Request. Vui lòng thử lại.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6 lg:p-10">
      <div className="flex items-center gap-3"><ClipboardList className="text-cyan-300" size={28} /><div><h1 className="text-2xl font-bold">Service Request Workbench</h1><p className="mt-1 text-sm text-slate-400">Hàng chờ fulfillment được tải từ hệ thống.</p></div></div>
      {loading && <div className="flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900 p-6 text-sm text-slate-300"><LoaderCircle className="animate-spin" size={18} />Đang tải hàng chờ…</div>}
      {error && <div role="alert" className="flex items-center gap-2 rounded-2xl border border-red-400/40 bg-red-400/10 p-5 text-sm text-red-100"><AlertCircle size={18} />{error}</div>}
      {!loading && !error && items.length === 0 && <div className="rounded-2xl border border-slate-700 bg-slate-900 p-12 text-center text-slate-400"><PackageOpen className="mx-auto mb-3" size={34} />Không có Service Request phù hợp trong hàng chờ.</div>}
      {!loading && !error && items.length > 0 && <div className="grid gap-3">
        {items.map((request) => <Link key={request.request_number} href={`/technician/requests/${request.request_number}`} className="rounded-2xl border border-slate-700 bg-slate-900 p-5 transition hover:border-cyan-500/70">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-mono text-xs text-cyan-300">{request.request_number}</p><h2 className="mt-1 font-semibold text-white">{request.service_name}</h2><p className="mt-2 text-sm text-slate-400">{request.fulfillment_group} · tạo {formatVietnamTime(request.created_at)}</p></div><div className="text-right text-sm"><p className="font-medium text-cyan-100">{statusLabel[request.status] ?? request.status}</p><p className="mt-1 text-slate-400">{request.assignee_name ? `Người xử lý: ${request.assignee_name}` : 'Chưa có người nhận'}</p></div></div>
        </Link>)}
      </div>}
    </main>
  );
}
