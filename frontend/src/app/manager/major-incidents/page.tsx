'use client';

import { AlertCircle, Siren } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function MajorIncidentWarRoomPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Major Incident War Room" subtitle="Kênh điều phối sự cố nghiêm trọng" />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>Broadcast chưa được kết nối.</strong><p className="mt-1">Không có integration gửi Email/Teams/Zalo hoặc audit backend cho broadcast. Giao diện không phát thông báo hay ghi timeline cục bộ như một sự kiện thật.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><Siren size={22} aria-hidden="true" /> Hãy dùng workflow Incident đã được hỗ trợ để theo dõi và escalation ticket.</section>
    </div>
  );
}
