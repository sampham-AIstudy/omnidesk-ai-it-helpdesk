'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Bell,
  Check,
  AlertTriangle,
  FileText,
  UserCheck,
  Sparkles,
  ChevronRight,
  Sliders,
} from 'lucide-react';

export default function NotificationCenterPage() {
  const [activeTab, setActiveTab] = useState<'feed' | 'settings'>('feed');

  useEffect(() => {
    document.title = 'Notification Center — Alerts & Preferences';
  }, []);

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Notification Center</span>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <h1 className="text-3xl font-semibold text-white tracking-tight flex items-center gap-3">
            <Bell className="text-cyan-400" size={32} />
            <span>Notification Center</span>
          </h1>
        </div>
      </header>

      {/* TABS */}
      <div className="mb-6 relative z-10 flex gap-2 border-b border-white/10 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab('feed')}
          className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer ${
            activeTab === 'feed' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
          }`}
        >
          Notification Feed
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer ${
            activeTab === 'settings' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
          }`}
        >
          Channel Preferences Settings
        </button>
      </div>

      {/* FEED CONTENT */}
      <div className="relative z-10 space-y-4">
        {activeTab === 'feed' && (
          <div className="space-y-3 max-w-3xl">
            <div className="rounded-2xl border border-red-400/30 bg-red-400/10 p-4 flex items-center gap-3">
              <span className="size-2.5 rounded-full bg-red-400 animate-ping shrink-0" />
              <div>
                <p className="text-xs font-semibold text-red-200">🔴 INC-1021 SLA breaches in 12 min</p>
                <p className="text-[10px] text-white/40 font-mono mt-0.5">14:20 • Network Team</p>
              </div>
            </div>

            <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 flex items-center gap-3">
              <span className="size-2.5 rounded-full bg-amber-400 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-amber-200">🟠 CHG-201 requires your CAB approval</p>
                <p className="text-[10px] text-white/40 font-mono mt-0.5">14:00 • Change Management</p>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 flex items-center gap-3">
              <span className="size-2.5 rounded-full bg-cyan-400 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-white">🔵 INC-992 technician Lê Minh Công replied</p>
                <p className="text-[10px] text-white/40 font-mono mt-0.5">13:45 • Support Desk</p>
              </div>
            </div>

            <div className="rounded-2xl border border-indigo-400/30 bg-indigo-400/10 p-4 flex items-center gap-3">
              <span className="size-2.5 rounded-full bg-indigo-400 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-indigo-200">🟣 AI requested HITL review for INC-10821</p>
                <p className="text-[10px] text-white/40 font-mono mt-0.5">13:30 • AI Governance</p>
              </div>
            </div>
          </div>
        )}

        {/* SETTINGS MATRIX */}
        {activeTab === 'settings' && (
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4 max-w-2xl">
            <h2 className="text-sm font-semibold text-white uppercase">Kênh Nhận Thông Báo</h2>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center border-b border-white/5 pb-2">
                <span>P1 Incidents</span>
                <span className="font-mono text-cyan-300">✓ Email ✓ In-App ✓ Slack ✓ Teams</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-2">
                <span>Ticket replies</span>
                <span className="font-mono text-cyan-300">✓ Email ✓ In-App</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-2">
                <span>SLA warnings</span>
                <span className="font-mono text-cyan-300">✓ Email ✓ In-App</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
