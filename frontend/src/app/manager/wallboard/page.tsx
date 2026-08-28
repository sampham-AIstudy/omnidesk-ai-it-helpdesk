'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Monitor, CheckCircle2, Clock, AlertTriangle, Activity, Star, RefreshCw, Maximize, ArrowLeft, ShieldAlert } from 'lucide-react';
import { formatVietnamTime } from '@/lib/utils';
import api from '@/lib/api';
import { Ticket, TicketListResponse } from '@/types';

export default function RealtimeWallboardPage() {
  const [now, setNow] = useState<string>('');
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const updateClock = () => {
      setNow(formatVietnamTime(new Date(), { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateClock();
    const interval = window.setInterval(updateClock, 1000);
    return () => window.clearInterval(interval);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // 1. Fetch live open tickets
  const { data: ticketsData, isLoading: isTicketsLoading } = useQuery({
    queryKey: ['wallboard-tickets'],
    queryFn: async () => (await api.get('/tickets?page_size=30')).data as TicketListResponse,
    refetchInterval: 5000,
  });

  // 2. Fetch live analytics overview
  const { data: analyticsData } = useQuery({
    queryKey: ['wallboard-analytics'],
    queryFn: async () => (await api.get('/analytics/overview')).data,
    refetchInterval: 10000,
  });

  const tickets = ticketsData?.items || [];
  const openCount = tickets.filter(t => ['open', 'in_progress', 'waiting_for_agent'].includes(t.status)).length;
  const hitlCount = tickets.filter(t => t.status === 'pending_hitl').length;
  const escalatedCount = tickets.filter(t => t.status === 'escalated' || t.sla_escalated).length;
  const pinnedCount = tickets.filter(t => t.is_pinned).length;

  return (
    <div className="enterprise-console min-h-screen bg-slate-950 text-white p-6 sm:p-10 space-y-8 font-sans selection:bg-blue-600 selection:text-white">
      {/* Wallboard Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link href="/manager/dashboard" className="w-10 h-10 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
            <ArrowLeft size={18} />
          </Link>
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center font-bold text-2xl shadow-lg shadow-blue-500/20">
            TV
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
              IT COMMAND CENTER & NOC WALLBOARD
            </h1>
            <p className="text-xs text-slate-400 font-mono flex items-center gap-2 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span>REAL-TIME LIVE STREAM • IT OPERATIONS ROOM TV</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={toggleFullscreen}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-xl text-xs font-bold text-slate-300 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Maximize size={14} />
            <span>{isFullscreen ? 'Thoát toàn màn hình' : 'Toàn màn hình (Kiosk)'}</span>
          </button>
          <div className="text-right">
            <div className="text-2xl font-mono font-bold text-cyan-400">{now}</div>
            <div className="text-[11px] text-slate-400 font-semibold uppercase">Giờ Chuẩn Vận Hành (GMT+7)</div>
          </div>
        </div>
      </div>

      {/* Big KPI Numbers Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sự Cố Đang Xử Lý</div>
          <div className="text-5xl font-bold text-blue-400 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {isTicketsLoading ? '...' : openCount.toString().padStart(2, '0')}
          </div>
          <div className="text-[11px] text-slate-400 font-medium">● Đang trực tuyến trong hàng đợi</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Chờ Phê Duyệt HITL</div>
          <div className="text-5xl font-bold text-amber-400 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {isTicketsLoading ? '...' : hitlCount.toString().padStart(2, '0')}
          </div>
          <div className="text-[11px] text-amber-400 font-medium">⚠️ Cần Quản lý / Admin ra quyết định</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sự Cố Leo Thang (Escalated)</div>
          <div className="text-5xl font-bold text-rose-500 font-mono" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {isTicketsLoading ? '...' : escalatedCount.toString().padStart(2, '0')}
          </div>
          <div className="text-[11px] text-rose-400 font-medium">⚡ Cần chuyên viên can thiệp trực tiếp</div>
        </div>

        <div className="bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-2 shadow-xl">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Ưu Tiên Gấp (Pinned Top)</div>
          <div className="text-5xl font-bold text-emerald-400 font-mono flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <span>{isTicketsLoading ? '...' : pinnedCount.toString().padStart(2, '0')}</span>
            <span className="text-2xl text-emerald-400">📌</span>
          </div>
          <div className="text-[11px] text-emerald-400 font-medium">Được ghim xử lý hỏa tốc</div>
        </div>
      </div>

      {/* Live Activity Stream & Active Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Live Active Tickets Stream (Span 8) */}
        <div className="lg:col-span-8 bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
              <Activity size={18} />
              <span>Hàng Đợi Sự Cố Hoạt Động Thời Gian Thực (Active Queue Stream)</span>
            </div>
            <span className="text-xs text-slate-500 font-mono">Tự động đồng bộ mỗi 5s</span>
          </div>

          <div className="space-y-3 font-mono text-xs max-h-[440px] overflow-y-auto">
            {tickets.slice(0, 8).map((ticket) => (
              <div key={ticket.id} className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800/80 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-slate-500 font-semibold">{formatVietnamTime(ticket.created_at, { hour: '2-digit', minute: '2-digit' })}</span>
                  {ticket.is_pinned && (
                    <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-amber-950 text-amber-400 border border-amber-800 flex-shrink-0">
                      📌 PINNED
                    </span>
                  )}
                  <span className={`px-2 py-0.5 rounded font-bold text-[10px] flex-shrink-0 ${
                    ticket.status === 'closed' || ticket.status === 'resolved' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    ticket.status === 'pending_hitl' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                    ticket.status === 'escalated' ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                    'bg-blue-950 text-blue-400 border border-blue-800'
                  }`}>
                    {ticket.ticket_number}
                  </span>
                  <span className="text-slate-300 font-sans text-xs truncate">{ticket.title}</span>
                </div>
                <span className="text-[11px] text-slate-500 uppercase flex-shrink-0">{ticket.status}</span>
              </div>
            ))}
            {tickets.length === 0 && (
              <div className="p-8 text-center text-slate-500">Hàng đợi đang trống.</div>
            )}
          </div>
        </div>

        {/* System Health Pulse (Span 4) */}
        <div className="lg:col-span-4 bg-slate-900/90 rounded-3xl p-6 border border-slate-800 space-y-4">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Trạng Thái Dịch Vụ Vận Hành (Services Health)
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">FastAPI Backend API</span>
                <span className="text-emerald-400">100% Sẵn Sàng (Live)</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full w-full" />
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">ChromaDB RAG Vector Store</span>
                <span className="text-cyan-400">Multi-lingual KB (Active)</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-cyan-500 h-full w-full" />
              </div>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-300">Zero-Mem Context Engine</span>
                <span className="text-purple-400">Memory Graph (Ready)</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-purple-500 h-full w-full" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
