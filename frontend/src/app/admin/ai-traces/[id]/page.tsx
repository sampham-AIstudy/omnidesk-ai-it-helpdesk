'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ChevronRight,
  ArrowLeft,
  Activity,
  Cpu,
  Clock,
  Coins,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Terminal,
} from 'lucide-react';
import { MOCK_TRACE_DETAIL } from '@/lib/aiGovernanceData';

export default function AIEvaluationTraceDetailPage() {
  const params = useParams();
  const traceId = params?.id as string;

  useEffect(() => {
    document.title = `AI Execution Trace — ${traceId || 'tr-8821'}`;
  }, [traceId]);

  const trace = MOCK_TRACE_DETAIL;

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <Link href="/admin/ai-review" className="hover:text-white transition-colors">
            AI Governance
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-cyan-300 font-mono">{trace.id}</span>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/admin/ai-review"
              className="size-9 rounded-lg border border-white/10 bg-white/[0.03] text-white/60 hover:text-white flex items-center justify-center"
            >
              <ArrowLeft size={16} />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                <Activity size={24} className="text-cyan-400" />
                <span>AI EXECUTION TRACE</span>
              </h1>
              <p className="text-xs text-white/50 mt-0.5 font-mono">Trace ID: {trace.id} • Ticket: {trace.ticketId}</p>
            </div>
          </div>
        </div>
      </header>

      {/* TOP METRICS SUMMARY CARDS */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-3 relative z-10">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">TOTAL LATENCY</span>
          <span className="text-xl font-bold text-cyan-300 mt-1 block font-mono">{trace.totalLatencyMs} ms</span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">TOKENS USED</span>
          <span className="text-xl font-bold text-blue-300 mt-1 block font-mono">{trace.tokensUsed}</span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">ESTIMATED COST</span>
          <span className="text-xl font-bold text-emerald-300 mt-1 block font-mono">{trace.costEstimate}</span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">MODEL & PROMPT</span>
          <span className="text-xs font-semibold text-white/80 mt-2 block truncate">{trace.promptVersion}</span>
        </div>
      </div>

      {/* WATERFALL EXECUTION TIMELINE */}
      <div className="grid xl:grid-cols-[1fr_360px] gap-6 relative z-10 items-start">
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6">
          <h2 className="text-sm font-semibold text-white uppercase flex items-center gap-2">
            <Cpu size={16} className="text-cyan-300" />
            <span>Execution Pipeline Waterfall</span>
          </h2>

          <div className="space-y-3 relative pl-4 border-l border-white/15">
            {trace.steps.map((step, idx) => (
              <motion.div
                key={step.name}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <span className={`size-2.5 rounded-full ${step.status === 'WARN' ? 'bg-amber-400' : 'bg-cyan-400'}`} />
                  <div>
                    <h3 className="text-sm font-semibold text-white">{step.name}</h3>
                    {step.details && <p className="text-xs text-amber-300/90 mt-0.5 font-mono">{step.details}</p>}
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="font-mono text-xs font-bold text-cyan-300">↓ {step.latencyMs} ms</span>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* SIDEBAR DEEP DIVE STATS */}
        <aside className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-5">
          <h2 className="text-sm font-semibold text-white uppercase">Deep Dive Attributes</h2>

          <div className="space-y-3 text-xs">
            <div className="border-b border-white/10 pb-2">
              <span className="text-white/40 block font-mono text-[10px]">GUARDRAIL RESULT</span>
              <span className="text-emerald-300 font-semibold">{trace.guardrailResult}</span>
            </div>

            <div className="border-b border-white/10 pb-2">
              <span className="text-white/40 block font-mono text-[10px]">RETRIEVED CHUNKS & SCORES</span>
              <div className="mt-1 space-y-1 font-mono">
                {trace.retrievedChunks.map((c) => (
                  <div key={c.id} className="flex justify-between text-[11px]">
                    <span className="text-cyan-300">{c.id}</span>
                    <span className="text-white/70">Score: {c.score}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-b border-white/10 pb-2">
              <span className="text-white/40 block font-mono text-[10px]">TOOL CALLS</span>
              <div className="mt-1 flex flex-wrap gap-1 font-mono text-[10px]">
                {trace.toolCalls.map((t) => (
                  <span key={t} className="bg-white/10 text-white/80 px-2 py-0.5 rounded">{t}</span>
                ))}
              </div>
            </div>

            <div>
              <span className="text-white/40 block font-mono text-[10px]">FINAL DECISION</span>
              <p className="text-xs text-white/90 font-medium leading-relaxed mt-1">{trace.finalDecision}</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
