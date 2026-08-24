'use client';

import { AlertCircle, ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/ui';

/** No mock HITL decisions: approving locally must never look persisted. */
export default function AIHumanReviewQueuePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="AI Human Review Queue" subtitle="Hàng đợi phê duyệt có kiểm soát" />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
        <AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" />
        <div><strong>Chưa có hàng đợi review đã persist.</strong><p className="mt-1 leading-6">Các thao tác approve, reject, chỉnh sửa và escalation bị vô hiệu hóa cho đến khi endpoint HITL có RBAC, audit trail và state transition được triển khai.</p></div>
      </section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600">
        <ShieldCheck className="text-slate-500" size={22} aria-hidden="true" /> Không có quyết định AI nào được giả lập hoặc thay đổi cục bộ trên trang này.
      </section>
    </div>
  );
}
