'use client';

import { AlertCircle, GitBranch } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function AutomationBuilderPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Tự động hóa vận hành" subtitle="Quy tắc tự động hóa cần được quản lý qua backend có audit." />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
        <AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" />
        <div><strong>Rule builder chưa khả dụng.</strong><p className="mt-1">Chưa có API, persistence hoặc audit trail cho việc tạo, bật/tắt hay xóa quy tắc. Không có rule nào được tạo hoặc thay đổi từ giao diện này.</p></div>
      </section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><GitBranch size={22} aria-hidden="true" /> Tính năng sẽ được mở lại cùng workflow quản trị đã được xác thực.</section>
    </div>
  );
}
