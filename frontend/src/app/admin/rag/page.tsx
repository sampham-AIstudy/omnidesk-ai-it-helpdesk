'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  Database,
  FileText,
  Layers,
  Cpu,
  CheckCircle2,
  Search,
  Play,
  ArrowUpRight,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import {
  MOCK_RAG_METRICS,
  MOCK_RETRIEVAL_RESULTS,
  KBRetrievalResult,
} from '@/lib/ragData';

export default function RAGPipelinePage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'playground' | 'documents' | 'index'>('overview');
  const [queryInput, setQueryInput] = useState('VPN không thể kết nối sau khi đổi mật khẩu');
  const [retrievedResults, setRetrievedResults] = useState<KBRetrievalResult[]>(MOCK_RETRIEVAL_RESULTS.default);
  const [isRunningRetrieval, setIsRunningRetrieval] = useState(false);

  useEffect(() => {
    document.title = 'RAG Knowledge Pipeline — Vector Search & Reranker';
  }, []);

  const handleRunRetrieval = () => {
    if (!queryInput.trim()) return;
    setIsRunningRetrieval(true);
    setTimeout(() => {
      setRetrievedResults(MOCK_RETRIEVAL_RESULTS.default);
      setIsRunningRetrieval(false);
      toast.success('Đã hoàn thành Hybrid Search + Cross-Encoder Reranking!');
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">RAG Pipeline</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <Database className="text-cyan-400" size={32} />
              <span>RAG Knowledge Pipeline</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Quản lý chỉ mục tri thức Vector DB, Hybrid Search (Dense + Sparse BM25) và Cross-Encoder Reranker phục vụ AI Agents.
            </p>
          </div>

          <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 px-4 py-2 rounded-full inline-flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>VECTOR DB: HEALTHY</span>
          </div>
        </div>
      </header>

      {/* TOP METRICS SUMMARY CARDS */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-3 relative z-10">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">DOCUMENTS</span>
          <span className="text-2xl font-bold text-white mt-1 block">
            {MOCK_RAG_METRICS.documentsCount.toLocaleString()}
          </span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">CHUNKS</span>
          <span className="text-2xl font-bold text-cyan-300 mt-1 block">
            {MOCK_RAG_METRICS.chunksCount.toLocaleString()}
          </span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">EMBEDDINGS</span>
          <span className="text-2xl font-bold text-blue-300 mt-1 block">
            {MOCK_RAG_METRICS.embeddingsCount.toLocaleString()}
          </span>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40 block">LAST INDEXING</span>
          <span className="text-sm font-semibold text-emerald-300 mt-2 block">
            {MOCK_RAG_METRICS.lastIndexingTime}
          </span>
        </div>
      </div>

      {/* TABS NAVIGATION */}
      <div className="mb-6 relative z-10">
        <div className="flex gap-2 border-b border-white/10 pb-3">
          {(['overview', 'playground', 'documents', 'index'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer capitalize ${
                activeTab === tab
                  ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40'
                  : 'text-white/50 hover:text-white'
              }`}
            >
              {tab === 'playground' ? 'Retrieval Test Playground' : tab}
            </button>
          ))}
        </div>
      </div>

      {/* TAB CONTENTS */}
      <div className="relative z-10 space-y-6">
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-white uppercase flex items-center gap-2">
                <Cpu size={16} className="text-cyan-300" />
                <span>Cấu hình Retriever Engine</span>
              </h2>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <span className="text-white/45">Chế độ Tìm kiếm</span>
                  <span className="font-mono text-cyan-300 font-bold">{MOCK_RAG_METRICS.retrieverEngine}</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <span className="text-white/45">Reranker Model</span>
                  <span className="font-mono text-emerald-300 font-bold">bge-reranker-large (Enabled)</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-2">
                  <span className="text-white/45">Vector Database</span>
                  <span className="font-mono text-white">ChromaDB / Qdrant Enterprise</span>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-white uppercase flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-300" />
                <span>Index Health & Benchmark</span>
              </h2>
              <div className="space-y-2 text-xs text-white/70">
                <p className="flex justify-between">
                  <span>Mean Reciprocal Rank (MRR):</span>
                  <strong className="font-mono text-cyan-300">0.87</strong>
                </p>
                <p className="flex justify-between">
                  <span>Recall@5 Benchmark:</span>
                  <strong className="font-mono text-emerald-300">92.3%</strong>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* PLAYGROUND TAB */}
        {activeTab === 'playground' && (
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Search size={18} className="text-cyan-300" />
              <span>Retrieval Playground (Thử nghiệm truy vấn RAG)</span>
            </h2>

            <div className="flex gap-3">
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Nhập câu hỏi thử nghiệm truy xuất tri thức..."
                className="flex-1 rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-white font-sans focus:border-cyan-400/60 focus:outline-none"
              />
              <button
                type="button"
                onClick={handleRunRetrieval}
                disabled={isRunningRetrieval}
                className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg hover:from-cyan-400 hover:to-blue-500 transition inline-flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <Play size={16} />
                <span>{isRunningRetrieval ? 'Đang chạy...' : 'Run Retrieval'}</span>
              </button>
            </div>

            {/* Results List */}
            <div className="space-y-3 pt-2">
              <span className="font-mono text-[10px] uppercase text-white/40 block">
                RETRIEVED CHUNKS ({retrievedResults.length})
              </span>

              {retrievedResults.map((kb, idx) => (
                <div
                  key={kb.id}
                  className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2 hover:border-cyan-400/40 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-cyan-300">#{idx + 1} {kb.id}</span>
                      <span className="text-sm font-medium text-white">{kb.title}</span>
                    </div>
                    <span className="font-mono text-xs font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 px-2.5 py-0.5 rounded">
                      Score: {kb.score}
                    </span>
                  </div>

                  <p className="text-xs text-white/70 leading-relaxed font-sans">{kb.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* DOCUMENTS & INDEX TABS */}
        {(activeTab === 'documents' || activeTab === 'index') && (
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-8 text-center text-xs text-white/50">
            <FileText size={32} className="mx-auto mb-2 text-white/20" />
            <p>Trạng thái danh sách tài liệu và tiến trình Indexing đang hoạt động bình thường.</p>
          </div>
        )}
      </div>
    </div>
  );
}
