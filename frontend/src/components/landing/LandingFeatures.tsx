'use client';

import Link from 'next/link';

export default function LandingFeatures() {
  return (
    <section id="features" className="py-24 px-6 md:px-12 bg-slate-50 border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full badge-glow-cyan text-[12px] font-semibold uppercase tracking-wider mb-4">
            Tính Năng Nổi Bật
          </div>
          <h2
            className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 tracking-tight leading-tight"
            style={{ fontFamily: 'Outfit, sans-serif' }}
          >
            Kiến Trúc IT Help Desk Thế Hệ Mới <br className="hidden sm:inline" /> Với AI Agent & RAG
          </h2>
          <p className="text-slate-600 text-base sm:text-lg font-medium mt-4">
            Tự động hóa quy trình hỗ trợ kỹ thuật, giảm 80% thời gian xử lý sự cố và nâng cao trải nghiệm làm việc cho toàn doanh nghiệp.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card 1: RAG Search (Span 2) */}
          <div className="md:col-span-2 glass-card-light glass-card-light-hover rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/5 rounded-full blur-2xl pointer-events-none" />
            <div>
              <div className="w-12 h-12 rounded-2xl bg-blue-600/10 text-blue-600 flex items-center justify-center font-bold text-xl mb-6">
                🔍
              </div>
              <span className="text-xs font-bold text-blue-600 uppercase tracking-widest">Tra Cứu Tri Thức Siêu Tốc</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Multi-Agent RAG với 392+ Tài Liệu Microsoft KB
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                Tích hợp Vector Database (ChromaDB) cùng mô hình nhúng đa ngôn ngữ `MiniLM-L12-v2`. Tìm chính xác câu trả lời từ tài liệu Microsoft chính thức cho sự cố Windows, Outlook, Office 365, Teams và Entra ID.
              </p>
            </div>

            {/* Interactive Mock Preview */}
            <div className="mt-8 p-4 rounded-2xl bg-slate-900 text-slate-100 font-mono text-xs space-y-2 border border-slate-800 shadow-inner">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                <span>RAG Service Execution</span>
                <span className="text-emerald-400">● 200 OK (0.18s)</span>
              </div>
              <div className="text-blue-400">QUERY &gt; &quot;Khắc phục lỗi không gửi được email Outlook PST&quot;</div>
              <div className="text-slate-300">RETRIEVED &gt; DocID: web-outlook-repair-datafile-001 (Match Score: 0.94)</div>
              <div className="text-emerald-300">SOLUTION &gt; Chạy công cụ Scanpst.exe để sửa tệp dữ liệu PST...</div>
            </div>
          </div>

          {/* Card 2: Auto Classification */}
          <div className="glass-card-light glass-card-light-hover rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-cyan-600/10 text-cyan-600 flex items-center justify-center font-bold text-xl mb-6">
                🎯
              </div>
              <span className="text-xs font-bold text-cyan-600 uppercase tracking-widest">Phân Loại Thông Minh</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Tự Động Đóng Ticket & Phân Luồng HITL
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                Hiển thị độ chắc chắn của bước phân loại. Câu trả lời và hành động chỉ được xác nhận khi có evidence, guardrail và workflow phù hợp.
              </p>
            </div>

            <div className="mt-8 space-y-3">
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-between">
                <span className="text-xs font-semibold text-emerald-800">Confidence &gt; 75%</span>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-600 text-white">Auto Close</span>
              </div>
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-between">
                <span className="text-xs font-semibold text-amber-800">Confidence 60-75%</span>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-amber-600 text-white">HITL Review</span>
              </div>
            </div>
          </div>

          {/* Card 3: Self-Service Solutions */}
          <div className="glass-card-light glass-card-light-hover rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-purple-600/10 text-purple-600 flex items-center justify-center font-bold text-xl mb-6">
                🛠️
              </div>
              <span className="text-xs font-bold text-purple-600 uppercase tracking-widest">Tự Khắc Phục</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Trung Tâm Self-Service IT
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                Hướng dẫn từng bước khắc phục lỗi phổ biến: Kết nối VPN, khôi phục khóa BitLocker, cài đặt máy in và thiết lập Microsoft Authenticator MFA.
              </p>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-200/80 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">28+ Danh mục quy trình</span>
              <Link href="/login" className="text-xs font-bold text-blue-600 hover:underline">
                Khám phá ngay →
              </Link>
            </div>
          </div>

          {/* Card 4: SLA & Analytics (Span 2) */}
          <div className="md:col-span-2 glass-card-light glass-card-light-hover rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 text-indigo-600 flex items-center justify-center font-bold text-xl mb-6">
                📊
              </div>
              <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Quản Lý Chuẩn Doanh Nghiệp</span>
              <h3 className="text-2xl font-bold text-slate-900 mt-2 mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Giám Sát SLA & Phân Quyền 3 Vai Trò (Role-Based Access)
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                Phân quyền cho **User** (Tạo ticket & chat AI), **Chuyên viên** (hàng đợi xử lý, tiếp nhận ticket và theo dõi SLA), và **Admin** (cấu hình và governance).
              </p>
            </div>

            <div className="mt-8 grid grid-cols-3 gap-4">
              <div className="p-4 rounded-2xl bg-slate-100/80 text-center border border-slate-200/60">
                <div className="text-lg font-bold text-slate-900">Employee</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Tạo Yêu Cầu & Chat AI</div>
              </div>
              <div className="p-4 rounded-2xl bg-blue-50 text-center border border-blue-200/60">
                <div className="text-lg font-bold text-blue-700">Technician</div>
                <div className="text-[11px] text-blue-600 mt-0.5">Xử Lý & Leo Thang SLA</div>
              </div>
              <div className="p-4 rounded-2xl bg-purple-50 text-center border border-purple-200/60">
                <div className="text-lg font-bold text-purple-700">Admin</div>
                <div className="text-[11px] text-purple-600 mt-0.5">Quản trị & Governance</div>
              </div>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}
