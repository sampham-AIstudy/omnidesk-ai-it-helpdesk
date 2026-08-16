'use client';

import { AlertCircle, Clock } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function SLAMatrixPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="SLA Matrix Management" subtitle="Cấu hình SLA chỉ được quản lý khi có persistence và audit contract." />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>Ma trận SLA chưa có nguồn cấu hình đã xác thực.</strong><p className="mt-1">Trang không hiển thị SLA mẫu như một cam kết sản phẩm và không có thao tác lưu cục bộ.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><Clock size={22} aria-hidden="true" /> SLA sẽ được hiển thị khi API quản trị có phân quyền và audit trail được triển khai.</section>
    </div>
  );
}
