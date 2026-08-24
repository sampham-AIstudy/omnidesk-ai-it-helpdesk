'use client';

import { AlertCircle, Bot, ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/ui';

/**
 * AI runtime configuration is deployment-controlled.  Keeping this page
 * read-only prevents local UI state from being presented as a policy change.
 */
export default function AIConsolePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="AI Console" subtitle="Trạng thái quản trị AI" />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
        <AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" />
        <p>Chế độ thực thi, guardrail và phản hồi đánh giá chưa có API quản trị được lưu vết. Trang này không cho phép thay đổi cấu hình AI.</p>
      </section>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="glass-card-light rounded-3xl border border-slate-200 p-6">
          <div className="mb-3 flex items-center gap-2 text-slate-900"><Bot size={20} /><h2 className="font-bold">Chế độ thực thi</h2></div>
          <p className="text-sm leading-6 text-slate-600">Cấu hình runtime được xác định bởi môi trường triển khai đã được phê duyệt; giao diện không suy diễn hoặc thay đổi chế độ này.</p>
        </section>
        <section className="glass-card-light rounded-3xl border border-slate-200 p-6">
          <div className="mb-3 flex items-center gap-2 text-slate-900"><ShieldCheck size={20} /><h2 className="font-bold">Guardrail</h2></div>
          <p className="text-sm leading-6 text-slate-600">Chính sách an toàn vẫn được thực thi ở backend. Việc cập nhật chính sách cần một luồng quản trị có RBAC, persistence và audit trước khi được mở trong UI.</p>
        </section>
      </div>
    </div>
  );
}
