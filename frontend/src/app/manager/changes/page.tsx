'use client';

import { AlertCircle, GitBranch } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function ChangeManagementPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Change Management" subtitle="Quản lý thay đổi có kiểm soát" />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>Tạo Change Request chưa khả dụng.</strong><p className="mt-1">Chưa có workflow CAB, persistence hoặc audit backend. Giao diện không tạo Change Request hoặc gửi phê duyệt giả lập.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><GitBranch size={22} aria-hidden="true" /> Khi workflow được triển khai, mọi thay đổi sẽ có trạng thái, actor và audit trail thực.</section>
    </div>
  );
}
