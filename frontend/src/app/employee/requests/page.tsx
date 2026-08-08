'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  LifeBuoy,
  Package,
  Search,
  PackageOpen,
  CheckCircle2,
  Circle,
  FileClock,
} from 'lucide-react';
import {
  MOCK_REQUESTS,
  STATUS_META,
  PRIORITY_META,
  STATUS_SEQUENCE,
  ServiceRequest,
  StatusKey,
  PriorityKey,
} from '@/lib/serviceRequestsData';

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Tất cả trạng thái' },
  { value: 'in_progress', label: 'Đang xử lý' },
  { value: 'COMPLETED', label: 'Hoàn tất' },
  { value: 'REJECTED', label: 'Từ chối' },
];

const PRIORITY_FILTER_OPTIONS = [
  { value: 'all', label: 'Tất cả ưu tiên' },
  { value: 'P0', label: 'P0 - Khẩn cấp' },
  { value: 'P1', label: 'P1 - Cao' },
  { value: 'P2', label: 'P2 - Trung bình' },
  { value: 'P3', label: 'P3 - Thấp' },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.2 } },
};

export default function ServiceRequestsListPage() {
  const router = useRouter();
  const [activeSegment, setActiveSegment] = useState<'requests' | 'incidents'>('requests');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  useEffect(() => {
    document.title = 'My Service Requests — Yêu Cầu Của Tôi';
  }, []);

  const filteredRequests = useMemo(() => {
    return MOCK_REQUESTS.filter((req) => {
      // Search query filter
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        req.id.toLowerCase().includes(q) ||
        req.title.toLowerCase().includes(q) ||
        req.category.toLowerCase().includes(q) ||
        req.items.some((item) => item.name.toLowerCase().includes(q));

      // Status filter
      let matchesStatus = true;
      if (statusFilter === 'in_progress') {
        matchesStatus = req.status !== 'COMPLETED' && req.status !== 'REJECTED';
      } else if (statusFilter !== 'all') {
        matchesStatus = req.status === statusFilter;
      }

      // Priority filter
      const matchesPriority = priorityFilter === 'all' || req.priority === priorityFilter;

      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [searchQuery, statusFilter, priorityFilter]);

  const handleCardClick = (id: string) => {
    router.push(`/employee/requests/${id}`);
  };

  const getProgressPercentage = (status: StatusKey) => {
    if (status === 'REJECTED') return 100;
    const index = STATUS_SEQUENCE.indexOf(status);
    if (index === -1) return 0;
    return Math.round((index / (STATUS_SEQUENCE.length - 1)) * 100);
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-8 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">My Service Requests</span>
        </div>

        {/* Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              My Service Requests{' '}
              <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Yêu Cầu Của Tôi
              </span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Theo dõi các yêu cầu dịch vụ (Service Request) — khác với Incident, mỗi request là một đơn xin sản phẩm/dịch vụ đi qua workflow phê duyệt & fulfillment.
            </p>
          </div>

          <div className="shrink-0">
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/50 flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 backdrop-blur">
              <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>SYNCED · REQ SERVER</span>
            </div>
          </div>
        </div>
      </header>

      {/* TYPE SEGMENTATION TABS */}
      <div className="mb-6 relative z-10">
        <div className="grid grid-cols-2 gap-2 w-full max-w-sm rounded-2xl border border-white/10 bg-black/40 p-1.5 backdrop-blur-md">
          {/* Tab 1: Incidents Link */}
          <Link
            href="/employee/tickets"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-white/10 bg-white/[0.02] text-white/50 hover:text-white transition-all text-center"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <LifeBuoy size={16} />
              <span>My Incidents</span>
            </div>
            <span className="font-mono text-[9px] text-white/40 mt-0.5">INC · Sự cố</span>
          </Link>

          {/* Tab 2: Requests (Active) */}
          <button
            type="button"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-cyan-400/60 bg-cyan-400/10 text-cyan-300 font-semibold transition-all text-center cursor-pointer shadow-md shadow-cyan-500/10"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <Package size={16} />
              <span>My Requests</span>
            </div>
            <span className="font-mono text-[9px] text-cyan-300/70 mt-0.5">REQ · Dịch vụ</span>
            <motion.div
              layoutId="seg"
              className="h-0.5 bg-cyan-400 absolute bottom-0 inset-x-4 rounded-full"
            />
          </button>
        </div>
      </div>

      {/* FILTER BAR */}
      <div className="mb-6 flex flex-col md:flex-row gap-3 relative z-10">
        {/* Search input */}
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo mã REQ hoặc tên dịch vụ..."
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3 pl-12 pr-4 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition font-sans"
          />
        </div>

        {/* Status select */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-white/10 bg-[#0c101c] px-4 py-3 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none cursor-pointer"
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#05070d] text-white">
              {opt.label}
            </option>
          ))}
        </select>

        {/* Priority select */}
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="rounded-xl border border-white/10 bg-[#0c101c] px-4 py-3 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none cursor-pointer"
        >
          {PRIORITY_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#05070d] text-white">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* REQUEST LIST */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {filteredRequests.length > 0 ? (
            <motion.div
              key="list"
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="space-y-4"
            >
              {filteredRequests.map((req) => {
                const statusMeta = STATUS_META[req.status];
                const priorityMeta = PRIORITY_META[req.priority];
                const StatusIcon = statusMeta.icon;
                const progressPct = getProgressPercentage(req.status);

                return (
                  <motion.div
                    key={req.id}
                    variants={cardVariants}
                    layout
                    onClick={() => handleCardClick(req.id)}
                    className="group rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 hover:border-cyan-400/40 hover:bg-white/[0.05] transition-all duration-300 cursor-pointer flex flex-col gap-4"
                  >
                    {/* Row 1: Request Info & Badges */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/80 font-medium">
                          {req.id}
                        </div>
                        <h2 className="text-white font-medium text-base mt-1 group-hover:text-cyan-300 transition-colors">
                          {req.title}
                        </h2>
                        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-white/45 font-sans">
                          <span>Ngày: {req.createdAt}</span>
                          <span>•</span>
                          <span>Người yêu cầu: {req.requester}</span>
                          <span>•</span>
                          <span>SL: {req.items.length} items</span>
                        </div>
                      </div>

                      {/* Right col badges */}
                      <div className="flex items-center gap-2 shrink-0">
                        {/* Priority Badge */}
                        <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-md ${priorityMeta.classNames}`}>
                          {priorityMeta.label}
                        </span>

                        {/* Status Chip */}
                        <span
                          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium`}
                        >
                          <span className={`size-1.5 rounded-full ${statusMeta.dotClass}`} />
                          <StatusIcon size={14} />
                          <span>{statusMeta.label}</span>
                        </span>

                        <ChevronRight
                          size={16}
                          className="text-white/25 group-hover:text-cyan-300 group-hover:translate-x-0.5 transition-all ml-1"
                        />
                      </div>
                    </div>

                    {/* Row 2: Progress Bar */}
                    <div className="hidden sm:block pt-1">
                      <div className="flex items-center justify-between mb-2 text-[11px] font-mono text-white/40">
                        <div className="flex items-center gap-2">
                          {STATUS_SEQUENCE.map((stKey, idx) => {
                            const currentIdx = STATUS_SEQUENCE.indexOf(req.status);
                            const isDone = req.status === 'COMPLETED' || currentIdx > idx;
                            const isCurrent = req.status === stKey;

                            return (
                              <div key={stKey} className="flex items-center gap-1">
                                {isDone ? (
                                  <CheckCircle2 size={13} style={{ color: STATUS_META[stKey].color }} />
                                ) : isCurrent ? (
                                  <CheckCircle2 size={13} className="text-cyan-400 animate-pulse" />
                                ) : (
                                  <Circle size={13} className="text-white/20" />
                                )}
                                <span
                                  className={`text-[10px] ${
                                    isDone
                                      ? 'text-white/70'
                                      : isCurrent
                                      ? 'text-cyan-300 font-semibold'
                                      : 'text-white/25'
                                  }`}
                                >
                                  {STATUS_META[stKey].label}
                                </span>
                                {idx < STATUS_SEQUENCE.length - 1 && (
                                  <span className="text-white/20 ml-1">•</span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        <span>{progressPct}%</span>
                      </div>

                      {/* Thin Progress line */}
                      <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-500 rounded-full"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Row 3: Item Chips */}
                    <div className="pt-2 border-t border-white/10 flex flex-wrap gap-2">
                      {req.items.map((item) => {
                        const itemStatusMeta = STATUS_META[item.status];
                        return (
                          <div
                            key={item.id}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] text-white/60 inline-flex items-center gap-1.5 font-sans"
                          >
                            <span className={`size-1.5 rounded-full ${itemStatusMeta.dotClass}`} />
                            <span>{item.name}</span>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          ) : (
            /* EMPTY STATE */
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="py-20 text-center flex flex-col items-center justify-center rounded-3xl border border-white/10 bg-white/[0.02]"
            >
              <PackageOpen size={40} className="text-white/20 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Chưa có yêu cầu dịch vụ nào</p>
              <p className="mt-1 text-sm text-white/45">Bấm 'Yêu Cầu Dịch Vụ' để tạo request đầu tiên.</p>
              <Link
                href="/employee/catalog"
                className="mt-5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-blue-500 transition cursor-pointer inline-flex items-center gap-2"
              >
                <span>Tạo Yêu Cầu Mới</span>
                <ChevronRight size={16} />
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
