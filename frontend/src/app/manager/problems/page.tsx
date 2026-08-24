'use client';

import { AlertCircle, Layers } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function ProblemManagementPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Problem Management" subtitle="Hồ sơ problem cần được quản lý bằng dữ liệu đã persist." />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>Tạo Problem Record chưa khả dụng.</strong><p className="mt-1">Chưa có API và audit contract cho liên kết incident hoặc lưu root cause. Không có Problem Record nào được tạo từ giao diện này.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><Layers size={22} aria-hidden="true" /> Tránh dùng state cục bộ như một hồ sơ vận hành.</section>
    </div>
  );
}
