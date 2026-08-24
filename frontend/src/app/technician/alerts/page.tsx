'use client';

import Link from 'next/link';
import { AlertCircle, BellRing } from 'lucide-react';

/** Alert acknowledgement/suppression needs a persisted monitoring integration. */
export default function AlertEventConsolePage() {
  return (
    <div className="enterprise-console min-h-screen rounded-3xl bg-[#05070d] p-6 text-white lg:p-10">
      <div className="mx-auto max-w-3xl space-y-6 pt-8">
        <div className="flex items-center gap-3"><BellRing className="text-cyan-300" size={28} /><h1 className="text-2xl font-bold">Alert / Event Console</h1></div>
        <section className="flex gap-3 rounded-2xl border border-amber-400/40 bg-amber-400/10 p-5 text-sm text-amber-100"><AlertCircle className="mt-0.5 shrink-0 text-amber-300" size={18} aria-hidden="true" /><div><strong>Chưa có nguồn alert đã persist.</strong><p className="mt-1 leading-6">ACK, suppress, assignment và tạo incident từ alert đã bị tắt vì chưa có API monitoring, state transition và audit trail. Không có alert hoặc incident nào được thay đổi cục bộ.</p></div></section>
        <Link href="/technician/queue" className="inline-flex rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-black">Mở hàng đợi ticket thực</Link>
      </div>
    </div>
  );
}
