'use client';

import Link from 'next/link';
import { Activity, CircleAlert } from 'lucide-react';

/**
 * This public page deliberately does not infer operational health.  The
 * application has no public status API yet, so publishing hard-coded uptime
 * and "all operational" values would be a false production claim.
 */
export default function PublicStatusPage() {
  return (
    <div className="status-page min-h-screen bg-slate-50 text-slate-900 selection:bg-cyan-300 selection:text-slate-950 p-6 md:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">
              <Activity size={16} /> OmniDesk AI • Public Status Center
            </div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Trạng thái hoạt động hệ thống CNTT
            </h1>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all self-start sm:self-auto"
          >
            ← Về Trang Chủ
          </Link>
        </div>

        <section className="rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-950 shadow-sm" aria-labelledby="status-unavailable-title">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
              <CircleAlert size={24} aria-hidden="true" />
            </div>
            <div className="space-y-2">
              <h2 id="status-unavailable-title" className="text-lg font-bold">
                Chưa có dữ liệu trạng thái thời gian thực
              </h2>
              <p className="text-sm leading-6 text-amber-900">
                Cổng trạng thái công khai chưa được kết nối với nguồn giám sát đã xác thực. Trang này không công bố uptime, độ trễ hoặc tình trạng dịch vụ khi chưa có dữ liệu thực.
              </p>
              <p className="text-xs font-medium text-amber-800">
                Nếu cần hỗ trợ, hãy tạo yêu cầu qua cổng Help Desk để đội ngũ xác minh tình trạng dịch vụ.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
