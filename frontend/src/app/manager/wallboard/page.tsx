'use client';

import { useState, useEffect } from 'react';
import { Monitor, CheckCircle2, Clock, AlertTriangle, Activity, Star, RefreshCw } from 'lucide-react';
import { formatVietnamTime } from '@/lib/utils';

export default function RealtimeWallboardPage() {
  const [now, setNow] = useState<string>('');

  useEffect(() => {
    const updateClock = () => {
      setNow(formatVietnamTime(new Date(), { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    const initialTimer = window.setTimeout(updateClock, 0);
    const interval = window.setInterval(updateClock, 1000);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="enterprise-console min-h-screen bg-slate-950 text-white p-6 sm:p-10 space-y-8 font-sans selection:bg-blue-600 selection:text-white">
      {/* Wallboard Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center font-bold text-2xl shadow-lg shadow-blue-500/20">
            TV
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
              IT HELP DESK REAL-TIME WALLBOARD
            </h1>
            <p className="text-xs text-slate-400 font-mono flex items-center gap-2 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span>LIVE STREAM MONITORING • ROOM SMART TV VIEW</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-2xl font-mono font-bold text-cyan-400">{now}</div>
            <div className="text-[11px] text-slate-400 font-semibold uppercase">Hệ Thống Đang Trực Bão Hòa</div>
          </div>
        </div>
      </div>

      {/* Big KPI Numbers Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tổng Ticket Đang Mở</div>
          <div className="text-5xl font-bold text-blue-400 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            24
          </div>
          <div className="text-[11px] text-emerald-400 font-medium">↓ 12% so với giờ cao điểm trước</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Quá Hạn SLA Hôm Nay</div>
          <div className="text-5xl font-bold text-rose-500 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            01
          </div>
          <div className="text-[11px] text-rose-400 font-medium">⚠️ 1 Ticket chờ HITL cần duyệt</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Số Agent IT Đang Trực</div>
          <div className="text-5xl font-bold text-emerald-400 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            08
          </div>
          <div className="text-[11px] text-slate-400 font-medium">● 6 Level 1 • 2 Level 2 Admin</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Điểm CSAT Hài Lòng Tuần</div>
          <div className="text-5xl font-bold text-amber-400 font-mono flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <span>4.9</span>
            <span className="text-2xl text-amber-400">★</span>
          </div>
          <div className="text-[11px] text-emerald-400 font-medium">98.2% Đánh giá 5 sao</div>
        </div>
      </div>

      {/* Live Activity Stream & Active Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Live Activity Stream (Span 8) */}
        <div className="lg:col-span-8 bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
              <Activity size={18} />
              <span>Dòng Sự Kiện Thời Gian Thực (Live Activity Stream)</span>
            </div>
            <span className="text-xs text-slate-500 font-mono">Tự động cập nhật mỗi 3s</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {[
              { time: '20:42:15', event: 'TICKET #HD-99482 CLOSED', desc: 'Sửa lỗi Wi-Fi Windows 11 qua RAG KB Guide', type: 'success' },
              { time: '20:41:02', event: 'AI AUTO-RESOLUTION', desc: 'Tự động mở khóa tài khoản Entra SSPR cho user an.nguyen', type: 'info' },
              { time: '20:39:44', event: 'NEW TICKET CREATED', desc: '[VPN] Gián đoạn kết nối FortiClient khi WFH', type: 'warning' },
              { time: '20:35:10', event: 'HITL APPROVED BY ADMIN', desc: 'Cấp quyền truy cập thư mục kế toán cho user binh.tran', type: 'success' },
            ].map((item, idx) => (
              <div key={idx} className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800/80 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-slate-500 font-semibold">{item.time}</span>
                  <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                    item.type === 'success' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    item.type === 'info' ? 'bg-blue-950 text-blue-400 border border-blue-800' :
                    'bg-amber-950 text-amber-400 border border-amber-800'
                  }`}>
                    {item.event}
                  </span>
                  <span className="text-slate-300 font-sans text-xs">{item.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Health Pulse (Span 4) */}
        <div className="lg:col-span-4 bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-4">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Chỉ Số Sức Khỏe Máy Chủ
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">FastAPI Backend</span>
                <span className="text-emerald-400">99.9% Uptime</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full w-[99%]" />
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">ChromaDB Vector Index</span>
                <span className="text-cyan-400">392 KB Docs (Ready)</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-cyan-500 h-full w-full" />
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">Upstash Redis Cache</span>
                <span className="text-purple-400">Cache Hit Rate 94%</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-purple-500 h-full w-[94%]" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
