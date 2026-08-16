'use client';

import { AlertCircle, ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function RBACAssetsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="RBAC & CMDB Assets" subtitle="Dữ liệu tài sản và quyền phải đến từ nguồn đã được ủy quyền." />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>Dữ liệu CMDB/RBAC chưa được kết nối.</strong><p className="mt-1">Trang không hiển thị hồ sơ mẫu, không xuất tệp và không thay đổi quyền khi chưa có backend xác thực, RBAC server-side và audit trail.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><ShieldCheck size={22} aria-hidden="true" /> Chức năng sẽ khả dụng khi dữ liệu quản trị được persisted an toàn.</section>
    </div>
  );
}
