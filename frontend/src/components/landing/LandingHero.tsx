'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

const SUGGESTIONS = [
  { label: '📶 Sửa lỗi Wi-Fi Windows', query: 'Cách khắc phục sự cố kết nối Wi-Fi trên Windows' },
  { label: '🔒 Tự đặt lại mật khẩu SSPR', query: 'Xử lý lỗi tự đặt lại mật khẩu Microsoft Entra SSPR' },
  { label: '📧 Khôi phục tệp Outlook PST', query: 'Sửa lỗi tệp dữ liệu Outlook PST và OST bị hỏng' },
  { label: '💻 Màn hình xanh BSOD', query: 'Khắc phục lỗi màn hình xanh Windows stop code' },
  { label: '🛡️ Khóa BitLocker Key', query: 'Cách tìm khóa khôi phục BitLocker trong Windows' },
];

export default function LandingHero() {
  const router = useRouter();
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/login');
  };

  const handleChipClick = (suggestionQuery: string) => {
    setQuery(suggestionQuery);
    router.push('/login');
  };

  return (
    <section className="relative min-h-[92vh] w-full flex flex-col items-center justify-between pt-36 pb-16 px-6 md:px-12 bg-light-mesh overflow-hidden border-b border-slate-200/60">
      
      {/* Glow Mesh Elements */}
      <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-gradient-to-r from-blue-400/15 via-cyan-400/15 to-purple-400/10 blur-3xl pointer-events-none rounded-full" />

      {/* Main Hero Container */}
      <div className="max-w-5xl w-full mx-auto text-center relative z-10 flex flex-col items-center gap-8">
        
        {/* Top Feature Pill */}
        <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full badge-glow-blue text-[13px] font-semibold tracking-tight shadow-sm">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          <span>Multi-Agent RAG Engine • 392+ Tài liệu KB Microsoft & Windows</span>
        </div>

        {/* Hero Title */}
        <h1
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 leading-[1.15] max-w-4xl"
          style={{ fontFamily: 'Outfit, sans-serif' }}
        >
          Giải Quyết Sự Cố IT Tức Thì <br className="hidden sm:inline" />
          Với <span className="bg-gradient-to-r from-blue-600 via-cyan-600 to-indigo-600 bg-clip-text text-transparent">Trợ Lý AI Thông Minh</span>
        </h1>

        {/* Subtitle */}
        <p className="text-base sm:text-lg text-slate-600 max-w-2xl font-medium leading-relaxed">
          Tự động tra cứu 392+ tài liệu trợ giúp chuẩn Microsoft 365, khôi phục tài khoản SSPR, sửa lỗi Wi-Fi, VPN, Outlook và màn hình xanh trong vài giây.
        </p>

        {/* Interactive Search Box */}
        <div className="w-full max-w-2xl mt-2">
          <form
            onSubmit={handleSearch}
            className="glass-card-light rounded-2xl p-2 pl-6 flex items-center gap-3 shadow-xl shadow-blue-950/5 border border-slate-300/80 hover:border-blue-400 transition-all"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400 flex-shrink-0">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <input
              type="text"
              placeholder="Mô tả sự cố IT của bạn (ví dụ: Không thể kết nối VPN, hỏng file Outlook)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent text-[15px] text-slate-900 placeholder-slate-400 outline-none font-medium min-w-0"
            />
            <button
              type="submit"
              className="shimmer-button text-white px-6 py-3 rounded-xl font-semibold text-sm flex items-center gap-2 flex-shrink-0 active:scale-95 transition-transform"
            >
              <span>Hỏi AI</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </form>

          {/* Quick Suggestion Chips */}
          <div className="flex items-center justify-center flex-wrap gap-2 mt-4">
            <span className="text-[12px] font-semibold text-slate-400 mr-1">Gợi ý nhanh:</span>
            {SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                onClick={() => handleChipClick(s.query)}
                className="text-[12px] font-semibold px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300 transition-all cursor-pointer shadow-2xs"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Live System Metrics Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-4xl mt-8 pt-8 border-t border-slate-200/80">
          <div className="glass-card-light rounded-xl p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-emerald-600 font-bold text-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              100% Operational
            </div>
            <div className="text-[12px] text-slate-500 font-medium mt-1">Trạng thái hệ thống</div>
          </div>
          <div className="glass-card-light rounded-xl p-4 text-center">
            <div className="text-xl font-bold text-slate-900">392 KB Docs</div>
            <div className="text-[12px] text-slate-500 font-medium mt-1">ChromaDB Vector Index</div>
          </div>
          <div className="glass-card-light rounded-xl p-4 text-center">
            <div className="text-xl font-bold text-blue-600">98.4%</div>
            <div className="text-[12px] text-slate-500 font-medium mt-1">SLA Auto Resolution</div>
          </div>
          <div className="glass-card-light rounded-xl p-4 text-center">
            <div className="text-xl font-bold text-purple-600">Mistral + RAG</div>
            <div className="text-[12px] text-slate-500 font-medium mt-1">Multi-Agent AI Model</div>
          </div>
        </div>

      </div>

    </section>
  );
}

