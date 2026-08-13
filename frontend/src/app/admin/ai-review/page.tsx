'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  UserCheck,
  Check,
  Pencil,
  X,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  Bot,
} from 'lucide-react';
import { MOCK_HITL_QUEUE, HITLItem } from '@/lib/aiGovernanceData';

export default function AIHumanReviewQueuePage() {
  const [queue, setQueue] = useState<HITLItem[]>(MOCK_HITL_QUEUE);

  useEffect(() => {
    document.title = 'AI Human Review Queue — Responsible HITL';
  }, []);

  const handleApprove = (item: HITLItem) => {
    setQueue((prev) => prev.filter((i) => i.id !== item.id));
    toast.success(`Đã Approve quyết định AI cho ${item.id}!`);
  };

  const handleModify = (item: HITLItem) => {
    setQueue((prev) => prev.filter((i) => i.id !== item.id));
    toast.success(`Mở chỉnh sửa quyết định cho ${item.id}`);
  };

  const handleReject = (item: HITLItem) => {
    setQueue((prev) => prev.filter((i) => i.id !== item.id));
    toast.error(`Đã từ chối (Reject) quyết định AI cho ${item.id}`);
  };

  const handleEscalate = (item: HITLItem) => {
    setQueue((prev) => prev.filter((i) => i.id !== item.id));
    toast.success(`Đã leo thang ${item.id} cho Trưởng phòng IT!`);
  };

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">AI Review Queue</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <UserCheck className="text-amber-400" size={32} />
              <span>AI Human Review Queue (HITL)</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Hàng chờ quyết định AI chưa đạt ngưỡng tin cậy — con người làm chủ quyết định cuối cùng (Human-in-the-loop) đảm bảo Agentic AI an toàn và có trách nhiệm.
            </p>
          </div>

          <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-5 py-3 flex items-center gap-3 shrink-0">
            <span className="size-2.5 rounded-full bg-amber-400 animate-ping" />
            <div className="flex flex-col">
              <span className="font-mono text-[10px] uppercase text-amber-300 font-bold tracking-[0.15em]">
                REVIEW QUEUE
              </span>
              <span className="text-2xl font-bold text-white leading-none">{queue.length}</span>
            </div>
          </div>
        </div>
      </header>

      {/* QUEUE ITEMS LIST */}
      <div className="relative z-10 space-y-4">
        <AnimatePresence>
          {queue.length > 0 ? (
            queue.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="rounded-3xl border border-amber-400/30 bg-amber-400/[0.04] backdrop-blur-xl p-6 space-y-5"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/10">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-base font-bold text-amber-300">{item.id}</span>
                    <span className="text-xs text-white/50">Người gửi: {item.requester} • Lúc {item.createdAt}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-amber-300 bg-amber-400/10 border border-amber-400/30 px-3 py-1 rounded-full font-bold">
                      {item.hitlReason}
                    </span>
                    <Link
                      href={`/admin/ai-traces/tr-8821`}
                      className="font-mono text-[10px] text-cyan-300 underline hover:text-cyan-200"
                    >
                      Xem Trace Execution
                    </Link>
                  </div>
                </div>

                {/* Summary */}
                <p className="text-sm font-medium text-white/90">{item.summary}</p>

                {/* Classification Comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
                    <span className="text-[10px] font-mono text-white/40 uppercase">AI CLASSIFICATION</span>
                    <div className="flex justify-between items-center text-sm font-semibold text-white">
                      <span>Category: {item.category}</span>
                      <span className="font-mono text-amber-300">{(item.categoryConfidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
                    <span className="text-[10px] font-mono text-white/40 uppercase">ALTERNATIVE PROPOSAL</span>
                    <div className="flex justify-between items-center text-sm font-semibold text-white/70">
                      <span>Category: {item.alternativeCategory}</span>
                      <span className="font-mono text-white/40">{(item.altConfidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {/* AI Wants To Do */}
                <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.05] p-4 space-y-2">
                  <span className="font-mono text-[10px] text-cyan-300 uppercase font-bold tracking-[0.15em] flex items-center gap-1.5">
                    <Bot size={12} />
                    <span>AI WANTS TO EXECUTE</span>
                  </span>
                  <ul className="text-xs text-white/80 space-y-1 font-sans">
                    <li>→ Route to Team: <strong>{item.proposedAction.routeTeam}</strong></li>
                    <li>→ Set Priority: <strong>{item.proposedAction.priority}</strong></li>
                    <li>→ Send Article: <strong>{item.proposedAction.sendKb}</strong></li>
                  </ul>
                </div>

                {/* HITL ACTION BUTTONS */}
                <div className="pt-2 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => handleApprove(item)}
                    className="rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black px-5 py-2.5 text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-lg"
                  >
                    <Check size={14} />
                    <span>Approve</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleModify(item)}
                    className="rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white px-5 py-2.5 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                  >
                    <Pencil size={14} />
                    <span>Modify</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleReject(item)}
                    className="rounded-xl border border-red-400/40 bg-red-400/10 text-red-300 hover:bg-red-400/20 px-5 py-2.5 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                  >
                    <X size={14} />
                    <span>Reject</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleEscalate(item)}
                    className="rounded-xl border border-amber-400/40 bg-amber-400/10 text-amber-300 hover:bg-amber-400/20 px-5 py-2.5 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                  >
                    <TrendingUp size={14} />
                    <span>Escalate</span>
                  </button>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="py-20 text-center rounded-3xl border border-white/10 bg-white/[0.02]">
              <Sparkles size={40} className="text-white/20 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Hàng chờ HITL hiện tại trống</p>
              <p className="mt-1 text-xs text-white/45">Tất cả quyết định AI đã được xử lý xong.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
