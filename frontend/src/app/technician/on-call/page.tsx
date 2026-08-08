'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  RotateCcw,
  Phone,
  MessageSquare,
  BellRing,
  CalendarDays,
  PhoneCall,
  GitBranch,
  CalendarClock,
  Play,
  Pencil,
  History,
  Plus,
  Users,
  X,
  Network as NetworkIcon,
  Cloud as CloudIcon,
  ShieldCheck as ShieldIcon,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import {
  ON_CALL_TEAMS,
  MOCK_OVERRIDES,
  OnCallTeam,
  OnCallOverride,
  ContactMethod,
} from '@/lib/onCallData';

export default function OnCallEscalationPage() {
  const [activeSegment, setActiveSegment] = useState<'roster' | 'policy' | 'manage'>('roster');
  const [activeManageTab, setActiveManageTab] = useState<'schedules' | 'overrides' | 'rotation' | 'teams'>('schedules');

  // Clock state
  const [timeStr, setTimeStr] = useState('00:00:00');
  const [overridesList, setOverridesList] = useState<OnCallOverride[]>(MOCK_OVERRIDES);

  // Modals state
  const [showContactModal, setShowContactModal] = useState(false);
  const [selectedTeamForContact, setSelectedTeamForContact] = useState<OnCallTeam | null>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);

  // Simulator state
  const [simTeamId, setSimTeamId] = useState('network');
  const [simSeverity, setSimSeverity] = useState<'P1' | 'P2' | 'P3'>('P1');
  const [simRunning, setSimRunning] = useState(false);
  const [simStepIndex, setSimStepIndex] = useState(-1);
  const [simCompleted, setSimCompleted] = useState(false);

  // Clock Ticking
  useEffect(() => {
    document.title = 'On-Call & Escalation — Realtime Agent Shift';
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Icon mapper helper
  const renderTeamIcon = (iconName: string, color: string) => {
    let colorClasses = 'bg-cyan-400/10 text-cyan-300';
    if (color === 'amber') colorClasses = 'bg-amber-400/10 text-amber-300';
    if (color === 'red') colorClasses = 'bg-red-400/10 text-red-300';

    return (
      <div className={`size-11 rounded-xl ${colorClasses} flex items-center justify-center shrink-0 border border-white/10`}>
        {iconName === 'Network' && <NetworkIcon size={20} strokeWidth={1.75} />}
        {iconName === 'Cloud' && <CloudIcon size={20} strokeWidth={1.75} />}
        {iconName === 'ShieldCheck' && <ShieldIcon size={20} strokeWidth={1.75} />}
      </div>
    );
  };

  // Run Escalation Simulator
  const handleRunSimulator = () => {
    setSimRunning(true);
    setSimStepIndex(-1);
    setSimCompleted(false);

    // Step 0
    setTimeout(() => setSimStepIndex(0), 400);
    // Step 1
    setTimeout(() => setSimStepIndex(1), 1200);
    // Step 2
    setTimeout(() => setSimStepIndex(2), 2000);
    // Completed
    setTimeout(() => {
      setSimRunning(false);
      setSimCompleted(true);
    }, 2600);
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background radial glow accents */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/technician/queue" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">On-Call & Escalation</span>
        </div>

        {/* Header Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              On-Call & Escalation
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Ai đang trực lúc này và đường leo thang khi P1 xảy ra ngoài giờ — theo dõi theo thời gian thực, không cần đoán.
            </p>
          </div>

          {/* LIVE Clock Card */}
          <div className="shrink-0">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-3 flex items-center gap-4 backdrop-blur-md">
              <div className="flex flex-col">
                <span className="font-mono text-[10px] text-white/40 uppercase">GIỜ HIỆN TẠI</span>
                <span className="text-xl font-semibold text-white font-mono tracking-wider">{timeStr}</span>
              </div>
              <div className="flex flex-col">
                <span className="font-mono text-[10px] text-white/40 uppercase">HÔM NAY</span>
                <span className="text-xs text-white/70 font-medium">Thứ Sáu · 07/08/2026</span>
              </div>
              <div className="h-8 w-px bg-white/10" />
              <div className="flex items-center gap-2">
                <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-mono text-[10px] text-emerald-300 font-semibold uppercase">TRỰC HOẠT ĐỘNG</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* MODULE SEGMENT TABS */}
      <div className="mb-6 relative z-10">
        <div className="grid grid-cols-3 gap-2 w-full max-w-xl rounded-2xl border border-white/10 bg-black/40 p-1.5 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setActiveSegment('roster')}
            className={`relative py-2.5 px-4 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
              activeSegment === 'roster' ? 'text-cyan-300 bg-cyan-400/10 border border-cyan-400/40' : 'text-white/50 hover:text-white'
            }`}
          >
            <span>Người Trực</span>
            {activeSegment === 'roster' && (
              <motion.div layoutId="seg" className="h-0.5 bg-cyan-400 absolute bottom-0 inset-x-4 rounded-full" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveSegment('policy')}
            className={`relative py-2.5 px-4 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
              activeSegment === 'policy' ? 'text-cyan-300 bg-cyan-400/10 border border-cyan-400/40' : 'text-white/50 hover:text-white'
            }`}
          >
            <span>Escalation Policy</span>
            {activeSegment === 'policy' && (
              <motion.div layoutId="seg" className="h-0.5 bg-cyan-400 absolute bottom-0 inset-x-4 rounded-full" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveSegment('manage')}
            className={`relative py-2.5 px-4 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
              activeSegment === 'manage' ? 'text-cyan-300 bg-cyan-400/10 border border-cyan-400/40' : 'text-white/50 hover:text-white'
            }`}
          >
            <span>Quản lý</span>
            {activeSegment === 'manage' && (
              <motion.div layoutId="seg" className="h-0.5 bg-cyan-400 absolute bottom-0 inset-x-4 rounded-full" />
            )}
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* VIEW 1 — NGƯỜI TRỰC (ON-CALL NOW)                          */}
      {/* ========================================================= */}
      {activeSegment === 'roster' && (
        <div className="space-y-6 relative z-10">
          {/* TEAM SCHEDULE CARDS */}
          <div className="space-y-4">
            {ON_CALL_TEAMS.map((team) => {
              const primaryInitials = team.primary.name
                .split(' ')
                .map((n) => n[0])
                .join('')
                .slice(0, 2);
              const secondaryInitials = team.secondary?.name
                .split(' ')
                .map((n) => n[0])
                .join('')
                .slice(0, 2);

              return (
                <div
                  key={team.id}
                  className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 sm:p-6 hover:border-cyan-400/30 transition-all duration-300 space-y-5"
                >
                  {/* Card Header */}
                  <div className="flex items-center gap-3">
                    {renderTeamIcon(team.iconName, team.color)}

                    <div>
                      <h2 className="text-base font-semibold text-white">{team.name}</h2>
                      <p className="text-[11px] text-white/45 flex items-center gap-1.5 mt-0.5 font-sans">
                        <RotateCcw size={12} className="text-cyan-300" />
                        <span>Rotation: {team.rotation}</span>
                      </p>
                    </div>

                    <div className="ml-auto">
                      <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-cyan-300 bg-cyan-400/10 border border-cyan-400/30 px-3 py-1.5 rounded-full inline-flex items-center gap-1.5">
                        <span className="size-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        <span>TRỰC BÂY GIỜ</span>
                      </span>
                    </div>
                  </div>

                  {/* Members Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* PRIMARY CARD */}
                    <div className="rounded-2xl border-2 border-cyan-400/40 bg-cyan-400/[0.05] p-4 relative overflow-hidden flex items-center justify-between gap-3">
                      <div className="absolute -top-px -left-px rounded-br-xl bg-cyan-400 px-3 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.15em] text-black">
                        PRIMARY
                      </div>

                      <div className="flex items-center gap-3 pt-3">
                        <div className="size-11 rounded-full bg-cyan-400/15 text-cyan-300 flex items-center justify-center text-sm font-semibold border border-cyan-400/30 shrink-0">
                          {primaryInitials}
                        </div>

                        <div className="min-w-0">
                          <p className="text-sm font-medium text-white truncate">{team.primary.name}</p>
                          <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-white/45 font-sans">
                            <Phone size={12} className="text-cyan-300" />
                            <span>{team.primary.phone}</span>
                            <span>•</span>
                            <span className="font-mono text-[9px] uppercase text-cyan-300 bg-cyan-400/10 px-1.5 py-0.5 rounded">
                              {team.primary.via}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="rounded-lg border border-white/10 bg-black/30 px-2.5 py-1 font-mono text-xs text-white/70">
                          {team.primary.shiftStart} → {team.primary.shiftEnd}
                        </div>
                        <span className="font-mono text-[9px] text-cyan-300/80 block mt-1">CÒN 4H 32M</span>
                      </div>
                    </div>

                    {/* SECONDARY CARD */}
                    {team.secondary ? (
                      <div className="rounded-2xl border border-white/10 bg-white/[0.02] hover:border-white/25 p-4 relative flex items-center justify-between gap-3 transition">
                        <div className="absolute -top-px -left-px rounded-br-xl border-b border-r border-white/10 bg-white/[0.06] px-3 py-1 font-mono text-[9px] font-bold uppercase text-white/50">
                          SECONDARY
                        </div>

                        <div className="flex items-center gap-3 pt-3">
                          <div className="size-10 rounded-full bg-white/10 text-white/70 flex items-center justify-center text-xs font-semibold shrink-0">
                            {secondaryInitials}
                          </div>

                          <div className="min-w-0">
                            <p className="text-sm font-medium text-white/80 truncate">{team.secondary.name}</p>
                            <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-white/45 font-sans">
                              <Phone size={12} className="text-white/40" />
                              <span>{team.secondary.phone}</span>
                              <span>•</span>
                              <span className="font-mono text-[9px] uppercase text-white/50 bg-white/10 px-1.5 py-0.5 rounded">
                                {team.secondary.via}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="rounded-lg border border-white/10 bg-black/30 px-2.5 py-1 font-mono text-xs text-white/50">
                            {team.secondary.shiftStart} → {team.secondary.shiftEnd}
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* NO SECONDARY CHIP */
                      <div className="rounded-2xl border border-amber-400/30 bg-amber-400/[0.06] p-4 flex items-center justify-center text-center">
                        <span className="font-mono text-[10px] text-amber-300 font-semibold tracking-[0.15em] uppercase">
                          KHÔNG CÓ SECONDARY
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Card Footer */}
                  <div className="pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs text-white/45">
                    <div className="flex items-center gap-1.5">
                      <CalendarDays size={14} className="text-white/40" />
                      <span>{team.nextShiftInfo}</span>
                    </div>

                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedTeamForContact(team);
                          setShowContactModal(true);
                        }}
                        className="rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3.5 py-2 text-xs text-white/70 hover:text-white transition flex items-center gap-1.5 cursor-pointer font-medium"
                      >
                        <PhoneCall size={14} className="text-cyan-300" />
                        <span>Liên hệ</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveSegment('policy')}
                        className="rounded-xl bg-white/[0.06] border border-white/10 hover:border-cyan-400/40 px-3.5 py-2 text-xs text-white/80 hover:text-cyan-300 transition flex items-center gap-1.5 cursor-pointer font-medium"
                      >
                        <GitBranch size={14} />
                        <span>Xem Escalation</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* OVERRIDES BANNER */}
          <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-5 flex items-start gap-3.5 backdrop-blur-md">
            <CalendarClock size={20} className="text-amber-300 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-200 font-semibold">Override đang hiệu lực hôm nay</p>
              <p className="text-xs text-amber-300/80 mt-1 leading-relaxed">
                Security: Pham Van D đổi phiên với Le Van E (06/08 20:00 → 07/08 08:00). Lý do: việc gia đình.
              </p>
              <button
                type="button"
                onClick={() => {
                  setActiveSegment('manage');
                  setActiveManageTab('overrides');
                }}
                className="text-xs text-amber-200 underline underline-offset-4 hover:text-amber-100 mt-2 font-medium cursor-pointer"
              >
                Xem chi tiết danh sách Overrides
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* VIEW 2 — ESCALATION POLICY                                */}
      {/* ========================================================= */}
      {activeSegment === 'policy' && (
        <div className="space-y-6 relative z-10">
          {/* POLICY CARDS GRID */}
          <div className="space-y-4">
            {ON_CALL_TEAMS.map((team) => (
              <div key={team.id} className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 sm:p-6 space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {renderTeamIcon(team.iconName, team.color)}
                    <div>
                      <h2 className="text-base font-semibold text-white">{team.name}</h2>
                      <p className="text-[11px] text-white/45">Quy trình leo thang tự động khi sự cố P1/P2 không được ACK</p>
                    </div>
                  </div>

                  <div className="flex gap-1.5">
                    <span className="font-mono text-[10px] text-red-300 bg-red-400/10 border border-red-400/30 px-2.5 py-1 rounded-md font-semibold">
                      P1 CRITICAL
                    </span>
                    <span className="font-mono text-[10px] text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2.5 py-1 rounded-md font-semibold">
                      P2 HIGH
                    </span>
                  </div>
                </div>

                {/* ESCALATION STEPS FLOW */}
                <div className="pt-2">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 relative">
                    {team.escalation.map((step, idx) => (
                      <div key={step.level} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex items-center gap-3">
                        <div className="size-10 rounded-full border border-cyan-400/40 bg-cyan-400/10 text-cyan-300 flex items-center justify-center font-mono text-xs font-bold shrink-0">
                          0{step.level}
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-white truncate">{step.target}</p>
                          <p className="text-[11px] text-white/45 truncate mt-0.5">{step.targetPerson}</p>

                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="font-mono text-[9px] text-cyan-300 bg-cyan-400/10 px-1.5 py-0.5 rounded border border-cyan-400/20">
                              {step.delay}
                            </span>
                            <span className="font-mono text-[9px] text-white/35">KHÔNG ACK</span>
                          </div>
                        </div>

                        {idx < team.escalation.length - 1 && (
                          <ArrowRight size={14} className="text-white/20 hidden md:block shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Policy Footer Config */}
                <div className="pt-4 border-t border-white/10 flex flex-wrap justify-between gap-3 text-[11px] text-white/45">
                  <span>ACK Timeout: 5 phút • SMS: 2 lần • CALL: 3 lần • Push APP: 2 lần</span>
                  <span className="text-cyan-300 font-mono">Quy trình tự động kích hoạt bởi System Alert Engine</span>
                </div>
              </div>
            ))}
          </div>

          {/* ESCALATION SIMULATOR CARD */}
          <div className="rounded-3xl border border-indigo-400/20 bg-indigo-500/[0.04] backdrop-blur-xl p-6 space-y-5">
            <div className="flex items-center gap-2">
              <Play size={18} className="text-indigo-300" />
              <div>
                <h3 className="text-base font-semibold text-white">Mô Phỏng Quy Trình Escalation</h3>
                <p className="text-xs text-white/45 mt-0.5">
                  Chạy thử mô phỏng đường leo thang cho từng nhóm & độ ưu tiên sự cố.
                </p>
              </div>
            </div>

            {/* Simulator Controls */}
            <div className="flex flex-wrap gap-3 items-end pt-2">
              <div className="min-w-44">
                <label className="block mb-1 text-xs text-white/60">Nhóm kỹ thuật</label>
                <select
                  value={simTeamId}
                  onChange={(e) => setSimTeamId(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#05070d] p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                >
                  <option value="network">Network Team</option>
                  <option value="cloud">Cloud Team</option>
                  <option value="security">Security Team</option>
                </select>
              </div>

              <div>
                <label className="block mb-1 text-xs text-white/60">Mức ưu tiên</label>
                <div className="flex gap-1.5">
                  {(['P1', 'P2', 'P3'] as const).map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setSimSeverity(sev)}
                      className={`font-mono text-xs px-3 py-2 rounded-xl border transition cursor-pointer ${
                        simSeverity === sev
                          ? 'border-red-400/60 bg-red-400/10 text-red-300 font-bold'
                          : 'border-white/10 bg-white/[0.02] text-white/40'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleRunSimulator}
                disabled={simRunning}
                className="rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-400 hover:to-cyan-400 transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <Play size={16} />
                <span>{simRunning ? 'Đang mô phỏng...' : 'Chạy mô phỏng'}</span>
              </button>
            </div>

            {/* Timed Step Animation */}
            {simStepIndex >= 0 && (
              <div className="mt-4 space-y-3 pt-3 border-t border-white/10">
                <div className="space-y-2">
                  {simStepIndex >= 0 && (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-red-400" />
                        <span className="font-mono text-[10px] text-white/40">02:00:00</span>
                        <span>SMS & Gọi cho Primary: Nguyen Van A</span>
                      </div>
                      <span className="font-mono text-[10px] text-red-300 font-bold">KHÔNG ACK (05:00)</span>
                    </motion.div>
                  )}

                  {simStepIndex >= 1 && (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-red-400" />
                        <span className="font-mono text-[10px] text-white/40">02:05:00</span>
                        <span>SMS & Gọi cho Secondary: Tran Van B</span>
                      </div>
                      <span className="font-mono text-[10px] text-red-300 font-bold">KHÔNG ACK (10:00)</span>
                    </motion.div>
                  )}

                  {simStepIndex >= 2 && (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="rounded-xl border border-emerald-400/40 bg-emerald-400/10 p-3 text-xs flex items-center justify-between text-emerald-300 font-medium"
                    >
                      <div className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="font-mono text-[10px] text-emerald-200">02:10:00</span>
                        <span>GỌI TRỰC TIẾP CHO IT MANAGER — PHẠM THỊ DUNG</span>
                      </div>
                      <span className="font-mono text-[10px] text-emerald-300 font-bold">ACK · ĐÃ NHẬN</span>
                    </motion.div>
                  )}
                </div>

                {simCompleted && (
                  <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-xs text-emerald-200 font-medium flex items-center gap-2">
                    <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                    <span>Đã leo thang tới IT Manager — Pham Thi Dung (CALL). Vòng lặp dừng thành công!</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* VIEW 3 — QUẢN LÝ (MANAGE)                                 */}
      {/* ========================================================= */}
      {activeSegment === 'manage' && (
        <div className="space-y-6 relative z-10">
          {/* Subtabs Header */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-w-2xl rounded-2xl border border-white/10 bg-black/40 p-1.5 backdrop-blur-md">
            <button
              type="button"
              onClick={() => setActiveManageTab('schedules')}
              className={`py-2 px-3 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
                activeManageTab === 'schedules' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
              }`}
            >
              Schedules
            </button>
            <button
              type="button"
              onClick={() => setActiveManageTab('overrides')}
              className={`py-2 px-3 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
                activeManageTab === 'overrides' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
              }`}
            >
              Overrides ({overridesList.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveManageTab('rotation')}
              className={`py-2 px-3 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
                activeManageTab === 'rotation' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
              }`}
            >
              Rotation
            </button>
            <button
              type="button"
              onClick={() => setActiveManageTab('teams')}
              className={`py-2 px-3 text-xs font-semibold rounded-xl transition cursor-pointer text-center ${
                activeManageTab === 'teams' ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40' : 'text-white/50 hover:text-white'
              }`}
            >
              Teams & Contact
            </button>
          </div>

          {/* TAB A — SCHEDULES */}
          {activeManageTab === 'schedules' && (
            <div className="space-y-3">
              {ON_CALL_TEAMS.map((team) => (
                <div key={team.id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">{team.name} Schedule</h3>
                    <p className="text-[11px] text-white/45 mt-0.5">Shift 20:00 → 08:00 • Mon – Sun</p>
                  </div>

                  {/* 7-day mini blocks */}
                  <div className="hidden md:flex gap-1.5">
                    {['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'].map((day, idx) => (
                      <div
                        key={day}
                        className={`size-8 rounded-lg border flex items-center justify-center font-mono text-[10px] ${
                          idx === 4
                            ? 'ring-1 ring-cyan-400 border-cyan-400/60 text-cyan-300 font-bold bg-cyan-400/10'
                            : 'border-white/10 text-white/40 bg-white/[0.02]'
                        }`}
                      >
                        {day}
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <button type="button" onClick={() => toast.success('Mở chỉnh sửa ca trực')} className="p-2 rounded-lg border border-white/10 hover:bg-white/10 text-white/60 hover:text-white">
                      <Pencil size={14} />
                    </button>
                    <button type="button" onClick={() => toast.success('Xem lịch sử ca trực')} className="p-2 rounded-lg border border-white/10 hover:bg-white/10 text-white/60 hover:text-white">
                      <History size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB B — OVERRIDES */}
          {activeManageTab === 'overrides' && (
            <div className="space-y-4">
              <button
                type="button"
                onClick={() => setShowOverrideModal(true)}
                className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-blue-500 transition inline-flex items-center gap-2 cursor-pointer"
              >
                <Plus size={16} />
                <span>Tạo Override</span>
              </button>

              <div className="space-y-3">
                {overridesList.map((ovr) => (
                  <div key={ovr.id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{ovr.originalPerson} → {ovr.overridePerson}</p>
                      <p className="text-xs text-white/45 mt-0.5">{ovr.teamName} • {ovr.shiftTime} • Lý do: {ovr.reason}</p>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className={`font-mono text-[10px] px-2.5 py-1 rounded-md border font-semibold ${
                        ovr.status === 'ACTIVE'
                          ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                          : 'border-zinc-500/30 bg-zinc-500/10 text-zinc-400'
                      }`}>
                        {ovr.status === 'ACTIVE' ? 'ĐANG HIỆU LỰC' : 'ĐÃ HẾT HẠN'}
                      </span>

                      {ovr.status === 'ACTIVE' && (
                        <button
                          type="button"
                          onClick={() => {
                            setOverridesList((prev) => prev.map((o) => (o.id === ovr.id ? { ...o, status: 'EXPIRED' as const } : o)));
                            toast.error('Đã hủy Override');
                          }}
                          className="text-xs text-red-300 hover:underline cursor-pointer"
                        >
                          Hủy
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB C — ROTATION */}
          {activeManageTab === 'rotation' && (
            <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4">
              <h3 className="text-sm font-semibold text-white">Vòng Quay Trực (Rotation Chain)</h3>
              <div className="flex flex-wrap items-center gap-2 pt-2">
                {ON_CALL_TEAMS[0].members.map((mem, idx) => (
                  <div key={mem} className="flex items-center gap-2">
                    <div className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3.5 py-2 text-xs font-medium text-cyan-300">
                      {mem}
                    </div>
                    {idx < ON_CALL_TEAMS[0].members.length - 1 && (
                      <ArrowRight size={14} className="text-white/30" />
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-white/45 pt-2">
                Network • Chu kỳ 1 tuần • Thay đổi tự động lúc 20:00 Chủ Nhật • Người trực kế tiếp: Nguyen Van C (08/08 → 14/08)
              </p>
            </div>
          )}

          {/* TAB D — TEAMS & CONTACT */}
          {activeManageTab === 'teams' && (
            <div className="grid sm:grid-cols-2 gap-3">
              {ON_CALL_TEAMS.map((team) => (
                <div key={team.id} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white">{team.name} Roster</h4>
                    <span className="font-mono text-[10px] text-cyan-300">{team.members.length} MEMBERS</span>
                  </div>

                  <ul className="space-y-2 text-xs text-white/70">
                    {team.members.map((m) => (
                      <li key={m} className="flex justify-between items-center border-b border-white/5 pb-1.5">
                        <span>{m}</span>
                        <span className="font-mono text-[10px] text-white/40">0932 xxx xxx</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL 1: QUICK CONTACT */}
      <AnimatePresence>
        {showContactModal && selectedTeamForContact && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Liên hệ — {selectedTeamForContact.name}</h3>
                <button type="button" onClick={() => setShowContactModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                {/* Primary Contact Option */}
                <div className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 p-3.5 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-mono text-[10px] text-cyan-300 font-bold">PRIMARY ON-CALL</span>
                    <span className="text-xs text-cyan-200 font-semibold">{selectedTeamForContact.primary.name}</span>
                  </div>
                  <p className="font-mono text-sm text-white font-medium">{selectedTeamForContact.primary.phone}</p>

                  <div className="pt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        toast.success(`Đã phát cuộc gọi cho ${selectedTeamForContact.primary.name} (${selectedTeamForContact.primary.phone})`);
                        setShowContactModal(false);
                      }}
                      className="flex-1 rounded-lg bg-cyan-500 text-black py-2 text-xs font-bold hover:bg-cyan-400 transition cursor-pointer flex items-center justify-center gap-1.5"
                    >
                      <PhoneCall size={14} />
                      <span>Gọi ngay</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        toast.success(`Đã gửi tin nhắn SMS cho ${selectedTeamForContact.primary.name}`);
                        setShowContactModal(false);
                      }}
                      className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70 hover:text-white transition cursor-pointer"
                    >
                      <MessageSquare size={14} />
                    </button>
                  </div>
                </div>

                {/* Secondary Contact Option */}
                {selectedTeamForContact.secondary && (
                  <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3.5 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-[10px] text-white/40">SECONDARY ON-CALL</span>
                      <span className="text-xs text-white/80 font-medium">{selectedTeamForContact.secondary.name}</span>
                    </div>
                    <p className="font-mono text-sm text-white/80">{selectedTeamForContact.secondary.phone}</p>

                    <div className="pt-2 flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          toast.success(`Đã phát cuộc gọi cho ${selectedTeamForContact.secondary?.name}`);
                          setShowContactModal(false);
                        }}
                        className="flex-1 rounded-lg border border-white/10 bg-white/5 py-2 text-xs text-white hover:bg-white/10 transition cursor-pointer flex items-center justify-center gap-1.5 font-medium"
                      >
                        <Phone size={14} />
                        <span>Gọi Secondary</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-white/10 flex justify-between items-center text-[10px] text-white/40 font-mono">
                <span>Hệ thống tự ghi nhận lịch sử cuộc gọi</span>
                <button type="button" onClick={() => setShowContactModal(false)} className="hover:text-white underline">Đóng</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 2: CREATE OVERRIDE */}
      <AnimatePresence>
        {showOverrideModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Tạo Override Ca Trực</h3>
                <button type="button" onClick={() => setShowOverrideModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-xs text-white/60">Nhóm kỹ thuật</label>
                  <select className="w-full rounded-xl border border-white/10 bg-[#05070d] p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none">
                    <option value="network">Network Team</option>
                    <option value="cloud">Cloud Team</option>
                    <option value="security">Security Team</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block mb-1 text-xs text-white/60">Từ người</label>
                    <input type="text" defaultValue="Pham Van D" className="w-full rounded-xl border border-white/10 bg-black/30 p-2 text-xs text-white" />
                  </div>
                  <div>
                    <label className="block mb-1 text-xs text-white/60">Đến người (Thay thế)</label>
                    <input type="text" defaultValue="Le Van E" className="w-full rounded-xl border border-white/10 bg-black/30 p-2 text-xs text-white" />
                  </div>
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Thời gian hiệu lực</label>
                  <input type="text" defaultValue="07/08 20:00 → 08/08 08:00" className="w-full rounded-xl border border-white/10 bg-black/30 p-2 text-xs text-white font-mono" />
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Lý do thay phiên ca trực</label>
                  <textarea rows={2} defaultValue="Đổi ca cá nhân" className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-xs text-white resize-none" />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button type="button" onClick={() => setShowOverrideModal(false)} className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white">
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const newOvr: OnCallOverride = {
                      id: `ovr-${Date.now()}`,
                      teamId: 'network',
                      teamName: 'Network',
                      originalPerson: 'Pham Van D',
                      overridePerson: 'Le Van E',
                      shiftTime: '07/08 20:00 → 08/08 08:00',
                      reason: 'Đổi ca cá nhân',
                      status: 'ACTIVE',
                    };
                    setOverridesList((prev) => [newOvr, ...prev]);
                    setShowOverrideModal(false);
                    toast.success('Đã tạo ca trực Override mới!');
                  }}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-lg cursor-pointer"
                >
                  Tạo Override
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
