'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  Search,
  CheckCheck,
  CheckCircle2,
  Siren,
  BellOff,
  UserRound,
  Sparkles,
  Globe,
  OctagonAlert,
  X,
  Check,
  Radio,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import {
  MOCK_ALERTS,
  MOCK_CORRELATION_CLUSTER,
  SEVERITY_META,
  STATUS_META,
  formatElapsedTime,
  AlertItem,
  AlertSeverity,
  AlertStatus,
} from '@/lib/alertsData';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Tất cả trạng thái' },
  { value: 'ACTIVE', label: 'Hoạt động' },
  { value: 'ACKNOWLEDGED', label: 'Đã xác nhận' },
  { value: 'SUPPRESSED', label: 'Đã tắt tiếng' },
  { value: 'CONVERTED', label: 'Đã chuyển Incident' },
];

export default function AlertEventConsolePage() {
  const router = useRouter();

  const [alerts, setAlerts] = useState<AlertItem[]>(MOCK_ALERTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverities, setSelectedSeverities] = useState<AlertSeverity[]>([
    'CRITICAL',
    'HIGH',
    'MEDIUM',
    'INFO',
  ]);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [timeTick, setTimeTick] = useState(0);
  const [clusterDismissed, setClusterDismissed] = useState(false);
  const [convertedBanner, setConvertedBanner] = useState<string | null>(null);

  // Modals state
  const [showIncidentModal, setShowIncidentModal] = useState(false);
  const [showMajorModal, setShowMajorModal] = useState(false);
  const [showSuppressModal, setShowSuppressModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [targetAlertId, setTargetAlertId] = useState<string | null>(null);
  const [suppressReason, setSuppressReason] = useState('');
  const [suppressTime, setSuppressTime] = useState('4h');
  const [assigneeTech, setAssigneeTech] = useState('Lê Minh Công');

  // Refresh elapsed labels periodically. Updating each second re-rendered the
  // entire animated monitoring console and could overwhelm demo browsers.
  useEffect(() => {
    document.title = 'Alert / Event Console — Realtime Monitoring';
    const timer = setInterval(() => {
      setTimeTick((prev) => prev + 1);
    }, 15_000);
    return () => clearInterval(timer);
  }, []);

  // 15s Auto-refresh polling simulation
  useEffect(() => {
    const pollTimer = setInterval(() => {
      // Simulate silent refresh / status sync
      setAlerts((prev) => [...prev]);
    }, 15000);
    return () => clearInterval(pollTimer);
  }, []);

  // Toggle severity selection chip
  const toggleSeverity = (sev: AlertSeverity) => {
    setSelectedSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev]
    );
  };

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alt) => {
      const matchesSev = selectedSeverities.includes(alt.severity);
      const matchesStatus = selectedStatus === 'all' || alt.status === selectedStatus;
      const q = searchQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        alt.id.toLowerCase().includes(q) ||
        alt.source.toLowerCase().includes(q) ||
        alt.message.toLowerCase().includes(q) ||
        alt.metric.toLowerCase().includes(q);

      return matchesSev && matchesStatus && matchesQuery;
    });
  }, [alerts, selectedSeverities, selectedStatus, searchQuery, timeTick]);

  const criticalAlerts = filteredAlerts.filter((a) => a.severity === 'CRITICAL');
  const nonCriticalAlerts = filteredAlerts.filter((a) => a.severity !== 'CRITICAL');

  // Batch ACK action
  const handleBatchACK = () => {
    setAlerts((prev) =>
      prev.map((a) => (a.status === 'ACTIVE' ? { ...a, status: 'ACKNOWLEDGED' as AlertStatus } : a))
    );
    toast.success('Đã xác nhận (ACK) toàn bộ alert đang hoạt động!');
  };

  // Single ACK action
  const handleSingleACK = (id: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'ACKNOWLEDGED' as AlertStatus } : a))
    );
    toast.success(`Đã xác nhận alert ${id}`);
  };

  // Confirm Incident Creation
  const handleConfirmCreateIncident = (isMajor = false) => {
    const newIncId = isMajor
      ? `MI-${Math.floor(1000 + Math.random() * 9000)}`
      : `INC-${Math.floor(10000 + Math.random() * 90000)}`;

    // Convert cluster alerts or single target alert
    const targetClusterIds = targetAlertId
      ? [targetAlertId]
      : MOCK_CORRELATION_CLUSTER.alertIds;

    setAlerts((prev) =>
      prev.map((a) =>
        targetClusterIds.includes(a.id)
          ? { ...a, status: 'CONVERTED' as AlertStatus, convertedTicketId: newIncId }
          : a
      )
    );

    setShowIncidentModal(false);
    setShowMajorModal(false);
    setConvertedBanner(newIncId);
    toast.success(`Đã khởi tạo ${isMajor ? 'Major Incident' : 'Incident'} (${newIncId})!`);
  };

  // Confirm Suppress
  const handleConfirmSuppress = () => {
    if (!suppressReason.trim()) {
      toast.error('Vui lòng nhập lý do tắt tiếng.');
      return;
    }

    const targetIds = targetAlertId ? [targetAlertId] : MOCK_CORRELATION_CLUSTER.alertIds;

    setAlerts((prev) =>
      prev.map((a) =>
        targetIds.includes(a.id)
          ? {
              ...a,
              status: 'SUPPRESSED' as AlertStatus,
              suppressReason,
              suppressUntil: suppressTime,
            }
          : a
      )
    );

    setShowSuppressModal(false);
    toast.error('Đã tắt tiếng alert thành công.');
  };

  // Confirm Assign
  const handleConfirmAssign = () => {
    if (!targetAlertId) return;

    setAlerts((prev) =>
      prev.map((a) => (a.id === targetAlertId ? { ...a, assignee: assigneeTech } : a))
    );

    setShowAssignModal(false);
    toast.success(`Đã phân công ${targetAlertId} cho ${assigneeTech}!`);
  };

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Subtle background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-cyan-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/technician/queue" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Alert Console</span>
        </div>

        {/* Header Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              Alert / Event Console
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Giám sát sự kiện hạ tầng theo thời gian thực. Alert được AI tương quan cụm trước khi tạo Incident — đảm bảo đúng chuỗi: Monitoring → Alert → AI Correlation → Incident → Major Incident.
            </p>
          </div>

          {/* LIVE Counter Chip */}
          <div className="shrink-0">
            <div className="rounded-2xl border border-red-400/30 bg-red-400/10 px-5 py-3 flex items-center gap-3.5 backdrop-blur-md shadow-lg shadow-red-500/10">
              <span className="size-2.5 rounded-full bg-red-400 animate-ping" />
              <div className="flex flex-col">
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-red-300 font-semibold">
                  LIVE ALERTS
                </span>
                <span className="text-3xl font-bold text-white leading-none mt-0.5">38</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* CONVERTED SUCCESS BANNER */}
      {convertedBanner && (
        <div className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-4 flex items-center justify-between gap-4 relative z-10 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={24} className="text-emerald-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-200">
                Đã khởi tạo thành công bản ghi {convertedBanner}!
              </p>
              <p className="text-xs text-emerald-300/80 mt-0.5">
                Các alert thuộc cụm sự cố đã được liên kết và chuyển sang trạng thái CONVERTED.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => router.push(`/technician/tickets/${convertedBanner}`)}
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-bold transition shrink-0 cursor-pointer"
          >
            Mở ticket
          </button>
        </div>
      )}

      {/* FILTER BAR */}
      <div className="mb-6 flex flex-col md:flex-row gap-3 flex-wrap relative z-10">
        {/* Search Input */}
        <div className="flex-1 min-w-56 relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm nguồn, message, metric..."
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3 pl-12 pr-4 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition font-sans"
          />
        </div>

        {/* Severity Chips Multi-select */}
        <div className="flex gap-1.5 flex-wrap items-center">
          {(Object.keys(SEVERITY_META) as AlertSeverity[]).map((sev) => {
            const isSelected = selectedSeverities.includes(sev);
            const meta = SEVERITY_META[sev];
            return (
              <button
                key={sev}
                type="button"
                onClick={() => toggleSeverity(sev)}
                className={`font-mono text-xs px-3.5 py-2.5 rounded-xl border transition cursor-pointer font-semibold ${
                  isSelected
                    ? `${meta.borderClass} ${meta.bgClass} ${meta.textClass}`
                    : 'border-white/10 bg-white/[0.02] text-white/40 hover:text-white'
                }`}
              >
                {sev}
              </button>
            );
          })}
        </div>

        {/* Status Dropdown */}
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="rounded-xl border border-white/10 bg-[#0c101c] px-4 py-3 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none cursor-pointer"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#05070d] text-white">
              {opt.label}
            </option>
          ))}
        </select>

        {/* Batch ACK Button */}
        <button
          type="button"
          onClick={handleBatchACK}
          className="rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/10 px-4 py-3 text-sm text-white/70 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
        >
          <CheckCheck size={16} />
          <span>Xác nhận tất cả</span>
        </button>
      </div>

      {/* BODY GRID: Alert Feed & AI Correlation */}
      <div className="grid xl:grid-cols-[1fr_360px] gap-6 items-start relative z-10">
        {/* COLUMN 1 — ALERT FEED */}
        <section className="space-y-6">
          {/* CRITICAL ALERTS SECTION */}
          {criticalAlerts.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="size-2.5 rounded-full bg-red-400 animate-pulse" />
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-red-300 font-bold">
                  CRITICAL
                </span>
                <span className="font-mono text-[10px] text-white/35 font-medium">
                  {criticalAlerts.length} ALERTS
                </span>
                <div className="flex-1 h-px bg-red-400/20" />
              </div>

              <div className="space-y-3">
                <AnimatePresence>
                  {criticalAlerts.map((alt) => {
                    const elapsed = formatElapsedTime(alt.startTimestampMs);
                    const isConverted = alt.status === 'CONVERTED';
                    const isAck = alt.status === 'ACKNOWLEDGED';

                    return (
                      <motion.div
                        key={alt.id}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96 }}
                        className="group rounded-2xl border border-red-400/30 bg-red-400/[0.04] p-4 hover:border-red-400/60 hover:bg-red-400/[0.07] transition-all duration-300"
                      >
                        {/* Row 1: Source, Message, Elapsed */}
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3 min-w-0">
                            <span className="size-2.5 rounded-full bg-red-400 animate-ping mt-1.5 shrink-0" />
                            <div className="min-w-0">
                              <span className="font-mono text-[11px] text-red-300 font-bold">
                                {alt.source}
                              </span>
                              <h3 className="text-sm font-semibold text-white mt-0.5">
                                {alt.message}
                              </h3>
                              <p className="text-xs text-white/50 mt-1 font-sans">
                                Metric: {alt.metric}
                              </p>
                            </div>
                          </div>

                          <div className="text-right shrink-0">
                            <span className="font-mono text-[11px] text-red-300 font-bold block">
                              {elapsed}
                            </span>
                            <span className="font-mono text-[9px] text-white/35 block mt-1 tracking-wider uppercase">
                              ĐANG DIỄN RA
                            </span>
                          </div>
                        </div>

                        {/* Row 2: Footer & Actions */}
                        <div className="mt-3 pt-3 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                          <div className="font-mono text-[10px] text-white/40">
                            {alt.id} • {alt.firstSeen}
                            {alt.assignee && <span className="ml-2 font-sans text-cyan-300">• Giao cho: {alt.assignee}</span>}
                          </div>

                          {/* Actions */}
                          <div className="flex flex-wrap items-center gap-2">
                            {isConverted ? (
                              <span className="rounded-lg bg-emerald-400/10 border border-emerald-400/30 px-3 py-1.5 text-[11px] text-emerald-300 font-mono font-medium flex items-center gap-1.5">
                                <Check size={12} />
                                <span>ĐÃ CHUYỂN {alt.convertedTicketId}</span>
                              </span>
                            ) : (
                              <>
                                {isAck ? (
                                  <span className="rounded-lg bg-zinc-500/10 border border-zinc-500/30 px-3 py-1.5 text-[11px] text-zinc-300 font-medium">
                                    Đã xác nhận
                                  </span>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() => handleSingleACK(alt.id)}
                                    className="rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3 py-1.5 text-[11px] text-white/70 hover:text-white transition flex items-center gap-1 cursor-pointer font-medium"
                                  >
                                    <Check size={12} />
                                    <span>Xác nhận</span>
                                  </button>
                                )}

                                <button
                                  type="button"
                                  onClick={() => {
                                    setTargetAlertId(alt.id);
                                    setShowIncidentModal(true);
                                  }}
                                  className="rounded-lg bg-gradient-to-r from-red-500 to-orange-500 px-3 py-1.5 text-[11px] font-semibold text-white shadow-lg shadow-red-500/20 hover:from-red-400 hover:to-orange-400 transition flex items-center gap-1.5 cursor-pointer"
                                >
                                  <Siren size={12} />
                                  <span>Tạo Incident</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => {
                                    setTargetAlertId(alt.id);
                                    setShowSuppressModal(true);
                                  }}
                                  className="rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3 py-1.5 text-[11px] text-white/60 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
                                >
                                  <BellOff size={12} />
                                  <span>Suppress</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => {
                                    setTargetAlertId(alt.id);
                                    setShowAssignModal(true);
                                  }}
                                  className="rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3 py-1.5 text-[11px] text-white/60 hover:text-white transition flex items-center gap-1.5 cursor-pointer"
                                >
                                  <UserRound size={12} />
                                  <span>Assign</span>
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            </div>
          )}

          {/* HIGH / MEDIUM / INFO ALERTS SECTION */}
          {nonCriticalAlerts.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-3">
                <span className="size-2 rounded-full bg-cyan-400" />
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/60 font-bold">
                  MUTED / SECONDARY ALERTS
                </span>
                <span className="font-mono text-[10px] text-white/35 font-medium">
                  {nonCriticalAlerts.length} ALERTS
                </span>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              <div className="space-y-3">
                {nonCriticalAlerts.map((alt) => {
                  const meta = SEVERITY_META[alt.severity];
                  const elapsed = formatElapsedTime(alt.startTimestampMs);
                  const isAck = alt.status === 'ACKNOWLEDGED';

                  return (
                    <div
                      key={alt.id}
                      className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 hover:border-white/25 transition-all duration-300 space-y-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0">
                          <span className={`size-2.5 rounded-full ${meta.dotClass} mt-1.5 shrink-0`} />
                          <div className="min-w-0">
                            <span className="font-mono text-[11px] text-white/60 font-bold">
                              {alt.source}
                            </span>
                            <h4 className="text-sm font-medium text-white/80 mt-0.5">{alt.message}</h4>
                            <p className="text-xs text-white/40 mt-1">{alt.metric}</p>
                          </div>
                        </div>

                        <span className="font-mono text-[11px] text-white/40 shrink-0">{elapsed}</span>
                      </div>

                      <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-3">
                        <div className="font-mono text-[10px] text-white/30">
                          {alt.id} • {alt.firstSeen}
                          {alt.assignee && <span className="ml-2 font-sans text-cyan-300">• {alt.assignee}</span>}
                        </div>

                        <div className="flex items-center gap-2">
                          {isAck ? (
                            <span className="rounded-lg bg-zinc-500/10 border border-zinc-500/30 px-3 py-1 text-[11px] text-zinc-300 font-medium">
                              Đã xác nhận
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleSingleACK(alt.id)}
                              className="rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3 py-1 text-[11px] text-white/70 hover:text-white transition flex items-center gap-1 cursor-pointer font-medium"
                            >
                              <Check size={12} />
                              <span>Xác nhận</span>
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => {
                              setTargetAlertId(alt.id);
                              setShowAssignModal(true);
                            }}
                            className="rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/10 px-3 py-1 text-[11px] text-white/60 hover:text-white transition flex items-center gap-1 cursor-pointer"
                          >
                            <UserRound size={12} />
                            <span>Assign</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* EMPTY STATE */}
          {filteredAlerts.length === 0 && (
            <div className="py-20 text-center flex flex-col items-center justify-center rounded-3xl border border-white/10 bg-white/[0.02]">
              <Radio size={40} className="text-white/15 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Không có alert phù hợp</p>
              <p className="mt-1 text-sm text-white/45 flex items-center gap-1.5 justify-center">
                <CheckCircle2 size={16} className="text-emerald-400" />
                <span>Sạch sẽ. Hệ thống đang hoạt động bình thường.</span>
              </p>
            </div>
          )}
        </section>

        {/* COLUMN 2 — AI CORRELATION PANEL (STICKY) */}
        {!clusterDismissed && (
          <aside className="rounded-3xl border border-indigo-400/20 bg-indigo-500/[0.04] backdrop-blur-xl p-5 sticky top-20 self-start space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-300" />
                <span>AI Correlation</span>
              </h2>
              <div className="flex items-center gap-1.5 font-mono text-[9px] text-emerald-300 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded-full">
                <span className="size-1.5 bg-emerald-400 rounded-full animate-pulse" />
                <span>LIVE</span>
              </div>
            </div>

            {/* Summary Card */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
              <p className="text-sm text-white/80 font-medium">{MOCK_CORRELATION_CLUSTER.summary}</p>
              <p className="text-xs text-white/45 leading-relaxed">
                Trong 5 phút gần nhất, nhóm theo nguồn + metric + thời gian khởi phát.
              </p>
            </div>

            {/* Probable Service */}
            <div className="rounded-2xl border border-cyan-400/25 bg-cyan-400/[0.06] p-4 space-y-2">
              <span className="font-mono uppercase text-[10px] tracking-[0.15em] text-cyan-300 block">
                PROBABLE SERVICE
              </span>
              <div className="flex items-center justify-between">
                <span className="text-base font-semibold text-white">
                  {MOCK_CORRELATION_CLUSTER.serviceName}
                </span>
                <Globe size={20} className="text-cyan-300/80" />
              </div>
              <p className="text-xs text-white/50 leading-relaxed pt-1">
                {MOCK_CORRELATION_CLUSTER.description}
              </p>
            </div>

            {/* Cluster Member Alerts */}
            <div>
              <span className="font-mono uppercase text-[10px] tracking-[0.15em] text-white/40 block mb-2">
                CLUSTER ALERTS ({MOCK_CORRELATION_CLUSTER.alertIds.length})
              </span>
              <div className="space-y-1.5">
                {MOCK_CORRELATION_CLUSTER.alertIds.map((id) => {
                  const alt = alerts.find((a) => a.id === id);
                  return (
                    <div
                      key={id}
                      className="rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2 text-xs flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="size-1.5 rounded-full bg-red-400 shrink-0" />
                        <span className="font-mono text-[10px] text-white/50">{id}</span>
                        <span className="text-white/80 truncate">{alt?.source}</span>
                      </div>
                      <span className="font-mono text-[9px] text-red-300 shrink-0">CRITICAL</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Confidence Score */}
            <div>
              <div className="flex justify-between text-[10px] text-white/45 mb-1 font-mono">
                <span>Độ tin cậy cụm</span>
                <span className="text-indigo-300 font-bold">{MOCK_CORRELATION_CLUSTER.confidencePct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-400 to-cyan-400 rounded-full"
                  style={{ width: `${MOCK_CORRELATION_CLUSTER.confidencePct}%` }}
                />
              </div>
            </div>

            {/* AI Narrative */}
            <div className="rounded-xl border border-white/10 bg-black/20 p-3.5 text-xs text-white/60 leading-relaxed font-sans">
              {MOCK_CORRELATION_CLUSTER.aiNarrative}
            </div>

            {/* Actions Grid */}
            <div className="grid grid-cols-3 gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  setTargetAlertId(null);
                  setShowIncidentModal(true);
                }}
                className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-3 py-2.5 text-xs font-semibold text-white shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-blue-500 transition flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Siren size={14} />
                <span>Incident</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTargetAlertId(null);
                  setShowMajorModal(true);
                }}
                className="rounded-xl bg-gradient-to-r from-red-500 to-orange-500 px-3 py-2.5 text-xs font-semibold text-white shadow-lg shadow-red-500/25 hover:from-red-400 hover:to-orange-400 transition flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <OctagonAlert size={14} />
                <span>Major</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTargetAlertId(null);
                  setShowSuppressModal(true);
                }}
                className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-xs text-white/60 hover:text-white transition flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <BellOff size={14} />
                <span>Suppress</span>
              </button>
            </div>

            {/* Dismiss Suggestion */}
            <button
              type="button"
              onClick={() => {
                setClusterDismissed(true);
                toast.success('Đã ẩn gợi ý cụm AI');
              }}
              className="w-full text-[11px] text-white/40 hover:text-white transition flex items-center justify-center gap-1.5 cursor-pointer pt-2"
            >
              <X size={12} />
              <span>Bỏ qua gợi ý cụm này</span>
            </button>
          </aside>
        )}
      </div>

      {/* MODAL 1: CREATE INCIDENT */}
      <AnimatePresence>
        {showIncidentModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-red-400/30 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Siren size={18} className="text-red-400" />
                  <span>Khởi tạo Incident từ Alert</span>
                </h3>
                <button type="button" onClick={() => setShowIncidentModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-xs text-white/60">Tiêu đề Incident</label>
                  <input
                    type="text"
                    defaultValue={
                      targetAlertId
                        ? `Sự cố ${targetAlertId}: ${alerts.find((a) => a.id === targetAlertId)?.message}`
                        : `Sự cố cụm hạ tầng ${MOCK_CORRELATION_CLUSTER.serviceName}`
                    }
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-sm text-white font-sans focus:border-red-400/60 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Mức độ ưu tiên</label>
                  <span className="font-mono text-xs text-red-300 bg-red-400/10 border border-red-400/30 px-3 py-1 rounded-md inline-block">
                    P0 - CRITICAL
                  </span>
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Cụm Alert liên kết</label>
                  <div className="flex flex-wrap gap-1">
                    {(targetAlertId ? [targetAlertId] : MOCK_CORRELATION_CLUSTER.alertIds).map((id) => (
                      <span key={id} className="font-mono text-[10px] text-cyan-300 bg-cyan-400/10 px-2 py-0.5 rounded">
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowIncidentModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirmCreateIncident(false)}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-red-500 to-orange-500 text-xs font-semibold text-white shadow-lg cursor-pointer"
                >
                  Tạo Incident
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 2: CREATE MAJOR INCIDENT */}
      <AnimatePresence>
        {showMajorModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-red-500/40 bg-[#12080a] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-red-500/30 pb-3">
                <h3 className="text-base font-semibold text-red-300 flex items-center gap-2">
                  <OctagonAlert size={18} className="text-red-400" />
                  <span>Nâng Cấp MAJOR INCIDENT</span>
                </h3>
                <button type="button" onClick={() => setShowMajorModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <p className="text-xs text-red-200/80 bg-red-500/10 border border-red-500/30 p-3 rounded-xl">
                  Cảnh báo: Tạo Major Incident sẽ tự động mở War Room và gửi cảnh báo khẩn cấp cho On-Call Team.
                </p>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Tiêu đề Major Incident</label>
                  <input
                    type="text"
                    defaultValue={`Sự cố thảm họa hạ tầng ${MOCK_CORRELATION_CLUSTER.serviceName}`}
                    className="w-full rounded-xl border border-white/10 bg-black/40 p-2.5 text-sm text-white font-sans focus:border-red-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowMajorModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirmCreateIncident(true)}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-red-500 to-orange-500 text-xs font-semibold text-white shadow-lg cursor-pointer"
                >
                  Xác nhận Nâng Major
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 3: SUPPRESS */}
      <AnimatePresence>
        {showSuppressModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <BellOff size={18} className="text-amber-300" />
                  <span>Tắt tiếng Alert (Suppress)</span>
                </h3>
                <button type="button" onClick={() => setShowSuppressModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-xs text-white/60">Lý do tắt tiếng (Bắt buộc)</label>
                  <textarea
                    value={suppressReason}
                    onChange={(e) => setSuppressReason(e.target.value)}
                    placeholder="Ví dụ: Đang bảo trì máy chủ theo lịch, alert giả do diễn tập..."
                    rows={3}
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-sm text-white placeholder:text-white/25 focus:border-cyan-400/60 focus:outline-none transition resize-none"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Thời gian tắt tiếng</label>
                  <select
                    value={suppressTime}
                    onChange={(e) => setSuppressTime(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-[#05070d] p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  >
                    <option value="1h">1 giờ</option>
                    <option value="4h">4 giờ</option>
                    <option value="24h">24 giờ</option>
                    <option value="forever">Vĩnh viễn (Đến khi gỡ thủ công)</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowSuppressModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleConfirmSuppress}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-xs font-semibold text-black transition cursor-pointer"
                >
                  Tắt tiếng
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 4: ASSIGN */}
      <AnimatePresence>
        {showAssignModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <UserRound size={18} className="text-cyan-300" />
                  <span>Phân công người xử lý Alert</span>
                </h3>
                <button type="button" onClick={() => setShowAssignModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div>
                <label className="block mb-1.5 text-xs text-white/60">Chọn Kỹ Thuật Viên</label>
                <select
                  value={assigneeTech}
                  onChange={(e) => setAssigneeTech(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#05070d] p-3 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                >
                  <option value="Lê Minh Công">Lê Minh Công (Level 2 - Network)</option>
                  <option value="Phạm Thị Dung">Phạm Thị Dung (IT Lead)</option>
                  <option value="System Admin">System Admin (Super Admin)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleConfirmAssign}
                  className="px-4 py-2 rounded-xl bg-cyan-500 text-xs font-semibold text-black hover:bg-cyan-400 transition cursor-pointer"
                >
                  Xác nhận phân công
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
