'use client';

import { AlertCircle, Database } from 'lucide-react';
import { PageHeader } from '@/components/ui';

export default function AdminCMDBPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="CMDB & quản lý tài sản" subtitle="Dữ liệu cấu hình cần có nguồn DB được xác thực." />
      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"><AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" /><div><strong>CMDB quản trị chưa được kết nối.</strong><p className="mt-1">Nhập từ Active Directory và thêm tài sản chưa có API, persistence, RBAC và audit trail. Không có thay đổi CMDB nào được xác nhận từ giao diện này.</p></div></section>
      <section className="glass-card-light flex items-center gap-3 rounded-3xl border border-slate-200 p-6 text-sm text-slate-600"><Database size={22} aria-hidden="true" /> Chức năng đọc/ghi CMDB sẽ chỉ được mở sau khi nguồn dữ liệu được tích hợp.</section>
    </div>
  );
}
