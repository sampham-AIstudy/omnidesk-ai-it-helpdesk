'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  Network,
  Globe,
  Sliders,
  ShieldCheck,
  Key,
  Server,
  Database,
  ArrowDown,
  AlertTriangle,
  LifeBuoy,
  Bug,
  GitBranch,
  UserRound,
  Info,
  CheckCircle2,
  Loader2,
  OctagonAlert,
} from 'lucide-react';
import { MOCK_CMDB_GRAPH, CINode } from '@/lib/cmdbData';

export default function CMDBTopologyMapPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('ci-vpngw-01');

  useEffect(() => {
    document.title = 'CMDB Unified Topology Map — IT Infrastructure Graph';
  }, []);

  const selectedNode = MOCK_CMDB_GRAPH.find((n) => n.id === selectedNodeId) || MOCK_CMDB_GRAPH[2];

  // Upstream & Downstream lookup
  const upstreamNodes = MOCK_CMDB_GRAPH.filter((n) => selectedNode.upstream.includes(n.id));
  const downstreamNodes = MOCK_CMDB_GRAPH.filter((n) => selectedNode.downstream.includes(n.id));

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">CMDB Topology Map</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <Network className="text-cyan-400" size={32} />
              <span>CMDB Unified Topology Map</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Trực quan hóa quan hệ phụ thuộc CI (CI Relationships) theo thời gian thực — phân tích tác động trực tiếp tới Incident, Change, Problem và Business Services.
            </p>
          </div>

          <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-cyan-300 bg-cyan-400/10 border border-cyan-400/30 px-4 py-2 rounded-full inline-flex items-center gap-2">
            <span className="size-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>SERVICENOW UNIFIED GRAPH ENGINE</span>
          </div>
        </div>
      </header>

      {/* GRAPH WORKSPACE GRID */}
      <div className="grid xl:grid-cols-[1fr_360px] gap-6 relative z-10 items-start">
        {/* VISUAL TOPOLOGY GRAPH PANEL */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40">
              INFRASTRUCTURE TOPOLOGY GRAPH
            </span>
            <span className="text-xs text-white/45">Click vào nút CI để xem phân tích chi tiết</span>
          </div>

          {/* VERTICAL FLOW NODES */}
          <div className="flex flex-col items-center gap-4 py-4">
            {MOCK_CMDB_GRAPH.map((node, idx) => {
              const isSelected = node.id === selectedNodeId;
              const isUpstream = selectedNode.upstream.includes(node.id);
              const isDownstream = selectedNode.downstream.includes(node.id);

              let nodeBorder = 'border-white/15 bg-white/[0.03]';
              let nodeText = 'text-white/80';
              if (isSelected) {
                nodeBorder = 'border-cyan-400/80 bg-cyan-400/15 shadow-xl shadow-cyan-500/20 ring-2 ring-cyan-400/30';
                nodeText = 'text-cyan-300 font-bold';
              } else if (isUpstream) {
                nodeBorder = 'border-amber-400/50 bg-amber-400/10';
                nodeText = 'text-amber-300 font-semibold';
              } else if (isDownstream) {
                nodeBorder = 'border-emerald-400/50 bg-emerald-400/10';
                nodeText = 'text-emerald-300 font-semibold';
              }

              return (
                <div key={node.id} className="w-full max-w-lg flex flex-col items-center">
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    onClick={() => setSelectedNodeId(node.id)}
                    className={`w-full rounded-2xl border ${nodeBorder} p-4 transition-all duration-300 cursor-pointer flex items-center justify-between gap-4`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="size-10 rounded-xl bg-white/[0.05] border border-white/10 flex items-center justify-center text-cyan-300 shrink-0">
                        {node.kind === 'INTERNET' && <Globe size={20} />}
                        {node.kind === 'LOAD_BALANCER' && <Sliders size={20} />}
                        {node.kind === 'GATEWAY' && <Server size={20} />}
                        {node.kind === 'AUTHENTICATION' && <ShieldCheck size={20} />}
                        {node.kind === 'IDENTITY' && <Key size={20} />}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm ${nodeText}`}>{node.name}</span>
                          {isSelected && (
                            <span className="font-mono text-[9px] uppercase bg-cyan-400 text-black px-1.5 py-0.5 rounded font-bold">
                              SELECTED
                            </span>
                          )}
                          {isUpstream && (
                            <span className="font-mono text-[9px] uppercase bg-amber-400/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-400/40">
                              UPSTREAM
                            </span>
                          )}
                          {isDownstream && (
                            <span className="font-mono text-[9px] uppercase bg-emerald-400/20 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-400/40">
                              DOWNSTREAM
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-white/40 mt-0.5 font-mono">
                          ID: {node.id} • Owner: {node.owner}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`font-mono text-[10px] px-2.5 py-1 rounded-md border font-medium ${
                        node.status === 'OPERATIONAL'
                          ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                          : 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                      }`}>
                        {node.status}
                      </span>
                    </div>
                  </motion.div>

                  {idx < MOCK_CMDB_GRAPH.length - 1 && (
                    <div className="my-1 flex flex-col items-center text-white/25">
                      <div className="h-4 w-px bg-white/20" />
                      <ArrowDown size={14} className="text-cyan-400/60" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* SIDEBAR — CI DETAILS & IMPACT HIGHLIGHT */}
        <aside className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-5 sticky top-20">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div>
              <span className="font-mono text-[10px] text-cyan-300 font-bold uppercase">CI HIGHLIGHT</span>
              <h2 className="text-base font-semibold text-white mt-0.5">{selectedNode.name}</h2>
            </div>
            <span className="font-mono text-[10px] text-white/40">{selectedNode.id}</span>
          </div>

          {/* Risk Rating Card */}
          <div className="rounded-2xl border border-amber-400/30 bg-amber-400/[0.06] p-4 space-y-2">
            <div className="flex justify-between items-center text-xs text-amber-300 font-semibold">
              <span>RỦI RƠ ẢNH HƯỞNG (RISK SCORE)</span>
              <span className="font-mono text-sm">{selectedNode.riskScore} / 100</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-400 via-amber-400 to-red-500 rounded-full"
                style={{ width: `${selectedNode.riskScore}%` }}
              />
            </div>
          </div>

          {/* Upstream & Downstream Dependencies */}
          <div className="space-y-3 pt-1">
            <div>
              <span className="font-mono uppercase text-[10px] text-amber-300 font-semibold block mb-1">
                UPSTREAM DEPENDENCIES ({upstreamNodes.length})
              </span>
              {upstreamNodes.length > 0 ? (
                <div className="space-y-1">
                  {upstreamNodes.map((u) => (
                    <div key={u.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5 text-xs text-white/80 flex justify-between">
                      <span>{u.name}</span>
                      <span className="font-mono text-[10px] text-white/40">{u.id}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-white/35">Không có upstream (Top-level node)</span>
              )}
            </div>

            <div>
              <span className="font-mono uppercase text-[10px] text-emerald-300 font-semibold block mb-1">
                DOWNSTREAM DEPENDENCIES ({downstreamNodes.length})
              </span>
              {downstreamNodes.length > 0 ? (
                <div className="space-y-1">
                  {downstreamNodes.map((d) => (
                    <div key={d.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5 text-xs text-white/80 flex justify-between">
                      <span>{d.name}</span>
                      <span className="font-mono text-[10px] text-white/40">{d.id}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-white/35">Không có downstream (Leaf node)</span>
              )}
            </div>
          </div>

          {/* Affected Services */}
          <div>
            <span className="font-mono uppercase text-[10px] text-white/40 block mb-1.5">
              AFFECTED SERVICES ({selectedNode.affectedServices.length})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {selectedNode.affectedServices.map((svc) => (
                <span key={svc} className="rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-300 font-medium">
                  {svc}
                </span>
              ))}
            </div>
          </div>

          {/* Open Records Matrix */}
          <div className="pt-3 border-t border-white/10 grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5">
              <span className="font-mono text-sm font-bold text-red-400 block">{selectedNode.openIncidents.length}</span>
              <span className="font-mono text-[8px] text-white/40 uppercase">INCIDENTS</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5">
              <span className="font-mono text-sm font-bold text-orange-400 block">{selectedNode.openProblems.length}</span>
              <span className="font-mono text-[8px] text-white/40 uppercase">PROBLEMS</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5">
              <span className="font-mono text-sm font-bold text-blue-400 block">{selectedNode.openChanges.length}</span>
              <span className="font-mono text-[8px] text-white/40 uppercase">CHANGES</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
