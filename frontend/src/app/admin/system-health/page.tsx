'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ChevronRight,
  Activity,
  Server,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Play,
  RefreshCw,
  Layers,
} from 'lucide-react';
import {
  MOCK_INFRA_COMPONENTS,
  MOCK_OPERATIONS_JOBS,
} from '@/lib/systemHealthData';

export default function SystemHealthOperationsPage() {
  const [activeTab, setActiveTab] = useState<'infra' | 'jobs'>('infra');

  useEffect(() => {
    document.title = 'System Health & Operations Jobs — Admin Console';
  }, []);

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">System Health</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <Activity className="text-cyan-400" size={32} />
              <span>System Health & Operations Jobs</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Giám sát hạ tầng kỹ thuật sâu (Deep System Health): API Gateway, Database, Vector DB, Queue Depth và trạng thái các background worker.
            </p>
          </div>
        </div>
      </header>

      {/* SYSTEM METRICS BAR */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-3 relative z-10 font-mono">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="text-[9px] uppercase tracking-[0.15em] text-white/40 block">QUEUE DEPTH</span>
          <span className="text-2xl font-bold text-cyan-300 mt-1 block">23</span>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="text-[9px] uppercase tracking-[0.15em] text-white/40 block">P50 LATENCY</span>
          <span className="text-2xl font-bold text-emerald-300 mt-1 block">380 ms</span>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="text-[9px] uppercase tracking-[0.15em] text-white/40 block">P95 LATENCY</span>
          <span className="text-2xl font-bold text-amber-300 mt-1 block">1.8 s</span>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="text-[9px] uppercase tracking-[0.15em] text-white/40 block">ERROR RATE</span>
          <span className="text-2xl font-bold text-white mt-1 block">0.12%</span>
        </div>
      </div>

      {/* TABS NAVIGATION */}
      <div className="mb-6 relative z-10">
        <div className="flex gap-2 border-b border-white/10 pb-3">
          <button
            type="button"
            onClick={() => setActiveTab('infra')}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer ${
              activeTab === 'infra' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
            }`}
          >
            Infrastructure Components ({MOCK_INFRA_COMPONENTS.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('jobs')}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer ${
              activeTab === 'jobs' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
            }`}
          >
            Operation Jobs ({MOCK_OPERATIONS_JOBS.length})
          </button>
        </div>
      </div>

      {/* TAB CONTENT */}
      <div className="relative z-10 space-y-4">
        {activeTab === 'infra' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {MOCK_INFRA_COMPONENTS.map((comp) => (
              <div
                key={comp.name}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 flex flex-col justify-between gap-3 hover:border-cyan-400/40 transition"
              >
                <div>
                  <h3 className="text-xs font-semibold text-white">{comp.name}</h3>
                  {comp.details && <p className="text-[10px] text-white/40 mt-1 font-mono">{comp.details}</p>}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-white/10">
                  <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                    comp.status === 'HEALTHY'
                      ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/30'
                      : 'bg-amber-400/10 text-amber-300 border border-amber-400/30'
                  }`}>
                    {comp.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="space-y-3">
            {MOCK_OPERATIONS_JOBS.map((job) => (
              <div
                key={job.id}
                className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex items-center justify-between gap-4 font-sans text-xs"
              >
                <div>
                  <h4 className="font-semibold text-white">{job.name}</h4>
                  <p className="text-[10px] text-white/40 font-mono mt-0.5">Type: {job.type} • Last run: {job.lastRun}</p>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono text-[10px] text-cyan-300">Queue: {job.queueDepth}</span>
                  <span className={`font-mono text-[10px] font-bold px-2.5 py-1 rounded-md border ${
                    job.status === 'SUCCESS'
                      ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                      : 'border-cyan-400/30 bg-cyan-400/10 text-cyan-300'
                  }`}>
                    {job.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
