'use client';

import { AlertCircle } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface IntegrationItem {
  id: string;
  name: string;
  category: string;
  description: string;
}

const INTEGRATIONS: readonly IntegrationItem[] = [
  { id: 'ad_sso', name: 'Microsoft Entra ID / Active Directory SSO', category: 'Xác thực & đồng bộ người dùng', description: 'Kết nối SSO và đồng bộ danh tính cần được cấu hình qua backend được kiểm soát.' },
  { id: 'smtp_mail', name: 'SMTP Email Gateway & Exchange Server', category: 'Thông báo & email', description: 'Kết nối gửi email cần được cấu hình qua backend được kiểm soát.' },
  { id: 'teams_bot', name: 'Microsoft Teams & Zalo OA Bot Integrations', category: 'Kênh trao đổi', description: 'Kết nối bot và thông báo cần được cấu hình qua backend được kiểm soát.' },
  { id: 'chroma_rag', name: 'ChromaDB Vector Store & AI Engine', category: 'AI / tri thức', description: 'Cấu hình hạ tầng AI không được suy ra từ giao diện và không thể thay đổi cục bộ.' },
];

/**
 * There is currently no persisted integration-management API.  This page is
 * intentionally read-only until that API and its audit/RBAC contract exist.
 */
export default function AdminIntegrationsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản lý tích hợp hệ thống bên thứ ba"
        subtitle="Trạng thái và cấu hình tích hợp chỉ được hiển thị khi có nguồn backend đã xác thực."
      />

      <section className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" aria-label="Trạng thái cấu hình">
        <AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={18} aria-hidden="true" />
        <p>Giao diện quản trị tích hợp chưa được kết nối với API cấu hình có lưu vết. Không có thay đổi nào có thể được thực hiện từ trang này.</p>
      </section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {INTEGRATIONS.map((item) => (
          <article key={item.id} className="glass-card-light space-y-4 rounded-3xl border border-slate-200 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>{item.name}</h2>
                <p className="mt-1 text-[11px] font-semibold text-slate-500">{item.category}</p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">Chưa xác minh</span>
            </div>
            <p className="text-xs font-medium leading-relaxed text-slate-600">{item.description}</p>
            <div className="border-t border-slate-100 pt-3 text-xs font-medium text-slate-500">Cấu hình và bật/tắt tích hợp hiện chưa khả dụng trong giao diện.</div>
          </article>
        ))}
      </div>
    </div>
  );
}
