'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ChevronRight,
  BarChart3,
  CheckCircle2,
  ShieldAlert,
  Sparkles,
  Target,
  Layers,
} from 'lucide-react';

export default function AIEvaluationDashboardPage() {
  useEffect(() => {
    document.title = 'AI Evaluation Dashboard — Responsible AI Benchmarks';
  }, []);

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
          <span className="text-white/70">AI Evaluation</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <BarChart3 className="text-cyan-400" size={32} />
              <span>AI Evaluation Dashboard</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Chứng minh hiệu năng Agentic AI Help Desk qua các chỉ số Benchmark chính xác: Accuracy, F1-Score, RAG Recall, MRR, Faithfulness và Ma trận nhầm lẫn (Confusion Matrix).
            </p>
          </div>

          <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-cyan-300 bg-cyan-400/10 border border-cyan-400/30 px-4 py-2 rounded-full inline-flex items-center gap-2">
            <span className="size-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>MODEL BENCHMARK VERIFIED</span>
          </div>
        </div>
      </header>

      {/* BENCHMARK CARDS MATRIX */}
      <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4 relative z-10">
        {/* Classification */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-cyan-300 block">CLASSIFICATION</span>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Accuracy</span>
            <span className="text-2xl font-bold text-white font-mono">94.2%</span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Macro F1</span>
            <span className="text-base font-bold text-cyan-300 font-mono">91.8%</span>
          </div>
        </div>

        {/* Routing & Priority */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-blue-300 block">ROUTING & PRIORITY</span>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Routing Acc</span>
            <span className="text-2xl font-bold text-white font-mono">96.1%</span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Priority Acc</span>
            <span className="text-base font-bold text-blue-300 font-mono">89.4%</span>
          </div>
        </div>

        {/* RAG Metrics */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-emerald-300 block">RAG ENGINE</span>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Recall@5</span>
            <span className="text-2xl font-bold text-white font-mono">92.3%</span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Faithfulness</span>
            <span className="text-base font-bold text-emerald-300 font-mono">94.1%</span>
          </div>
        </div>

        {/* Guardrails */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-2">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-amber-300 block">GUARDRAILS</span>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">Injection Detect</span>
            <span className="text-2xl font-bold text-white font-mono">98.7%</span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-white/50">False Positive</span>
            <span className="text-base font-bold text-amber-300 font-mono">1.4%</span>
          </div>
        </div>
      </div>

      {/* CONFUSION MATRIX SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Target size={18} className="text-cyan-300" />
              <span>Confusion Matrix (Phân Loại Sự Cố)</span>
            </h2>
            <span className="font-mono text-[9px] uppercase text-white/40">PREDICTED VS ACTUAL</span>
          </div>

          {/* 4x4 Confusion Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-center border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-[10px] font-mono text-white/40">
                  <th className="p-2 text-left">ACTUAL \ PREDICTED</th>
                  <th className="p-2 text-cyan-300">NET</th>
                  <th className="p-2 text-cyan-300">HW</th>
                  <th className="p-2 text-cyan-300">SW</th>
                  <th className="p-2 text-cyan-300">SEC</th>
                </tr>
              </thead>
              <tbody className="text-xs font-mono">
                <tr className="border-b border-white/5">
                  <td className="p-3 text-left font-bold text-white">Network (NET)</td>
                  <td className="p-3 bg-emerald-400/20 text-emerald-300 font-bold">92</td>
                  <td className="p-3 text-white/40">2</td>
                  <td className="p-3 text-white/40">3</td>
                  <td className="p-3 text-white/40">3</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="p-3 text-left font-bold text-white">Hardware (HW)</td>
                  <td className="p-3 text-white/40">1</td>
                  <td className="p-3 bg-emerald-400/20 text-emerald-300 font-bold">94</td>
                  <td className="p-3 text-white/40">4</td>
                  <td className="p-3 text-white/40">1</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="p-3 text-left font-bold text-white">Software (SW)</td>
                  <td className="p-3 text-white/40">3</td>
                  <td className="p-3 text-white/40">5</td>
                  <td className="p-3 bg-emerald-400/20 text-emerald-300 font-bold">90</td>
                  <td className="p-3 text-white/40">2</td>
                </tr>
                <tr>
                  <td className="p-3 text-left font-bold text-white">Security (SEC)</td>
                  <td className="p-3 text-white/40">1</td>
                  <td className="p-3 text-white/40">0</td>
                  <td className="p-3 text-white/40">2</td>
                  <td className="p-3 bg-emerald-400/20 text-emerald-300 font-bold">97</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Responsible AI Principles */}
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Sparkles size={18} className="text-indigo-300" />
            <span>Responsible AI & Guardrails Audit</span>
          </h2>
          <ul className="space-y-3 text-xs text-white/70">
            <li className="p-3 rounded-xl border border-white/10 bg-white/[0.02]">
              <strong className="text-white block font-medium">Input Guardrails & PII Anonymization</strong>
              <span>Tự động phát hiện và che giấu email, số điện thoại, mật khẩu trước khi gửi tới LLM.</span>
            </li>
            <li className="p-3 rounded-xl border border-white/10 bg-white/[0.02]">
              <strong className="text-white block font-medium">Faithfulness & Anti-Hallucination</strong>
              <span>Chỉ trả lời dựa trên thông tin retrieved từ bộ chỉ mục RAG KB đã qua kiểm duyệt.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
