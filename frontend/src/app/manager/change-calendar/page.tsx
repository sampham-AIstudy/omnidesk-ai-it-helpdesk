'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ChevronRight,
  Calendar,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
  Clock,
  UserRound,
  Zap,
} from 'lucide-react';
import { MOCK_CHANGE_CALENDAR, ChangeCalendarItem } from '@/lib/changeCalendarData';

export default function ChangeCalendarPage() {
  useEffect(() => {
    document.title = 'Change Calendar & CAB Collision Detection';
  }, []);

  const collisions = MOCK_CHANGE_CALENDAR.filter((c) => c.hasCollision);

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/manager/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Change Calendar</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <Calendar className="text-cyan-400" size={32} />
              <span>Change Calendar & CAB Approval</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Lịch thực hiện thay đổi hạ tầng Tháng 8/2026 — phát hiện xung đột lịch (Collision Detection Engine) và phân loại Standard / Normal / Emergency.
            </p>
          </div>
        </div>
      </header>

      {/* COLLISION ALERT BANNER */}
      {collisions.length > 0 && (
        <div className="mb-6 rounded-2xl border border-red-400/40 bg-red-400/10 p-5 space-y-2 relative z-10 backdrop-blur-md">
          <div className="flex items-center gap-2 text-red-300 font-bold text-sm">
            <AlertTriangle size={18} />
            <span>COLLISION DETECTED! (PHÁT HIỆN XUNG ĐỘT LỊCH THAY ĐỔI HẠ TẦNG)</span>
          </div>
          <div className="text-xs text-red-200/90 leading-relaxed space-y-1 font-mono">
            <p>• CHG-102 modifies DB-PROD-01 (12/08/2026)</p>
            <p>• CHG-109 depends on DB-PROD-01 (12/08/2026)</p>
            <p className="text-white/80 font-sans mt-1">Đề xuất CAB: Dời lịch CHG-109 sang 13/08/2026 để tránh gián đoạn dịch vụ.</p>
          </div>
        </div>
      )}

      {/* AUGUST 2026 CALENDAR GRID */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6 relative z-10">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <h2 className="text-lg font-semibold text-white font-mono">THÁNG 8 / 2026</h2>
          <span className="font-mono text-[10px] text-cyan-300 uppercase">CAB APPROVAL WORKFLOW ACTIVE</span>
        </div>

        {/* 5-Day Week Grid */}
        <div className="grid grid-cols-5 gap-3 text-center">
          {['T2 (Mon)', 'T3 (Tue)', 'T4 (Wed)', 'T5 (Thu)', 'T6 (Fri)'].map((day) => (
            <div key={day} className="font-mono text-xs font-bold text-white/50 pb-2 border-b border-white/10">
              {day}
            </div>
          ))}

          {/* Cell 1 */}
          <div className="min-h-32 rounded-2xl border border-white/5 bg-white/[0.01] p-2 text-left">
            <span className="font-mono text-[10px] text-white/30">10 Aug</span>
          </div>
          {/* Cell 2 */}
          <div className="min-h-32 rounded-2xl border border-white/5 bg-white/[0.01] p-2 text-left">
            <span className="font-mono text-[10px] text-white/30">11 Aug</span>
          </div>

          {/* Cell 3 — Wed 12 Aug (Collision Day) */}
          <div className="min-h-32 rounded-2xl border border-red-400/30 bg-red-400/[0.04] p-2 text-left space-y-2">
            <span className="font-mono text-[10px] text-red-300 font-bold">12 Aug (Collision)</span>
            <div className="rounded-xl border border-red-400/40 bg-red-400/20 p-2 text-[10px] font-mono text-white">
              <span className="font-bold text-red-300">CHG-102</span> DB Upgrade
              <span className="block text-[8px] text-red-200 mt-0.5">HIGH RISK</span>
            </div>
            <div className="rounded-xl border border-amber-400/40 bg-amber-400/20 p-2 text-[10px] font-mono text-white">
              <span className="font-bold text-amber-300">CHG-109</span> Firewall Rule
            </div>
          </div>

          {/* Cell 4 */}
          <div className="min-h-32 rounded-2xl border border-white/5 bg-white/[0.01] p-2 text-left">
            <span className="font-mono text-[10px] text-white/30">13 Aug</span>
          </div>

          {/* Cell 5 — Fri 14 Aug (Emergency) */}
          <div className="min-h-32 rounded-2xl border border-white/5 bg-white/[0.01] p-2 text-left space-y-1">
            <span className="font-mono text-[10px] text-white/30">14 Aug</span>
            <div className="rounded-xl border border-blue-400/40 bg-blue-400/20 p-2 text-[10px] font-mono text-white">
              <span className="font-bold text-blue-300">CHG-115</span> Emergency Exchange
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
