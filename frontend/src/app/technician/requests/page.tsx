'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  Wrench,
  PackageCheck,
  Search,
  Filter,
  CheckCircle2,
  Loader2,
  OctagonAlert,
  Circle,
  UserRound,
  RefreshCw,
} from 'lucide-react';
import {
  MOCK_WORKBENCH_REQUESTS,
  TASK_STATUS_META,
  PRIORITY_META,
  deriveRequestStatus,
  RequestFulfillment,
  TaskStatus,
} from '@/lib/fulfillmentData';

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Tất cả trạng thái' },
  { value: 'need_action', label: 'Cần xử lý' },
  { value: 'IN_PROGRESS', label: 'Đang xử lý' },
  { value: 'BLOCKED', label: 'Bị chặn' },
  { value: 'COMPLETED', label: 'Hoàn tất' },
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

export default function FulfillmentWorkbenchListPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [onlyMine, setOnlyMine] = useState(false);
  const [sortP0First, setSortP0First] = useState(true);

  useEffect(() => {
    document.title = 'Request Fulfillment Workbench — IT Support';
  }, []);

  const filteredRequests = useMemo(() => {
    let result = MOCK_WORKBENCH_REQUESTS.filter((req) => {
      const derivedStatus = deriveRequestStatus(req.tasks);

      // Search query filter
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        req.id.toLowerCase().includes(q) ||
        req.title.toLowerCase().includes(q) ||
        req.requester.toLowerCase().includes(q) ||
        req.department.toLowerCase().includes(q) ||
        req.tasks.some((t) => t.name.toLowerCase().includes(q));

      // Status filter
      let matchesStatus = true;
      if (statusFilter === 'need_action') {
        matchesStatus = derivedStatus === 'PENDING' || derivedStatus === 'IN_PROGRESS';
      } else if (statusFilter !== 'all') {
        matchesStatus = derivedStatus === statusFilter;
      }

      // Assignee filter
      const matchesAssignee = !onlyMine || req.assignee === 'Lê Minh Công';

      return matchesSearch && matchesStatus && matchesAssignee;
    });

    if (sortP0First) {
      const pOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
      result = [...result].sort((a, b) => pOrder[a.priority] - pOrder[b.priority]);
    }

    return result;
  }, [searchQuery, statusFilter, onlyMine, sortP0First]);

  const handleCardClick = (id: string) => {
    router.push(`/technician/requests/${id}`);
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background radial glow accents */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-8 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/technician/queue" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Fulfillment Workbench</span>
        </div>

        {/* Header Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              Request Fulfillment Workbench
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Xử lý các Service Request được giao — hoàn thành từng fulfillment task theo đúng workflow. Khác với Incident Resolution: mỗi request có thể chứa nhiều task cấp phát, chạy tuần tự hoặc song song.
            </p>
          </div>

          {/* Right Stat Chips */}
          <div className="hidden md:flex items-center gap-3 shrink-0">
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-cyan-300 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 flex items-center gap-2 backdrop-blur">
              <span className="size-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>3 ĐANG XỬ LÝ</span>
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-emerald-300 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 flex items-center gap-2 backdrop-blur">
              <span className="size-2 rounded-full bg-emerald-400" />
              <span>12 ĐÃ HOÀN TẤT</span>
            </div>
          </div>
        </div>
      </header>

      {/* MODULE SEGMENTATION TABS */}
      <div className="mb-6 relative z-10">
        <div className="grid grid-cols-2 gap-2 w-full max-w-md rounded-2xl border border-white/10 bg-black/40 p-1.5 backdrop-blur-md">
          {/* Tab 1: Ticket Queue Link */}
          <Link
            href="/technician/queue"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-white/10 bg-white/[0.02] text-white/50 hover:text-white transition-all text-center"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <Wrench size={16} />
              <span>Ticket Queue</span>
            </div>
            <span className="font-mono text-[9px] text-white/40 mt-0.5">INC · Sự cố</span>
          </Link>

          {/* Tab 2: Fulfillment Workbench (Active) */}
          <button
            type="button"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-cyan-400/60 bg-cyan-400/10 text-cyan-300 font-semibold transition-all text-center cursor-pointer shadow-md shadow-cyan-500/10"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <PackageCheck size={16} />
              <span>Fulfillment Workbench</span>
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
            placeholder="Tìm REQ, tên nhân viên, phòng ban..."
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

        {/* Toggle "Của tôi" */}
        <button
          type="button"
          onClick={() => setOnlyMine(!onlyMine)}
          className={`rounded-xl border px-4 py-3 text-sm flex items-center justify-center gap-2 transition cursor-pointer ${
            onlyMine
              ? 'border-cyan-400/60 bg-cyan-400/10 text-cyan-300 font-semibold'
              : 'border-white/10 bg-white/[0.04] text-white/60 hover:text-white'
          }`}
        >
          <Filter size={15} />
          <span>Của tôi</span>
        </button>

        {/* Priority Sort Toggle */}
        <button
          type="button"
          onClick={() => setSortP0First(!sortP0First)}
          className={`rounded-xl border px-4 py-3 font-mono text-[10px] tracking-[0.15em] uppercase transition cursor-pointer ${
            sortP0First
              ? 'border-cyan-400/40 bg-white/[0.04] text-cyan-300'
              : 'border-white/10 bg-white/[0.02] text-white/40'
          }`}
        >
          SẮP XẾP: P0 → P3
        </button>
      </div>

      {/* REQUEST CARDS LIST */}
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
                const derivedStatus = deriveRequestStatus(req.tasks);
                const statusMeta = TASK_STATUS_META[derivedStatus];
                const priorityMeta = PRIORITY_META[req.priority];
                const completedTasks = req.tasks.filter((t) => t.status === 'COMPLETED').length;
                const totalTasks = req.tasks.length;
                const progressPct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

                return (
                  <motion.div
                    key={req.id}
                    variants={cardVariants}
                    layout
                    onClick={() => handleCardClick(req.id)}
                    className="group rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 hover:border-cyan-400/40 hover:bg-white/[0.05] transition-all duration-300 cursor-pointer flex flex-col gap-4"
                  >
                    {/* Row 1: Request Header & Status */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/80 font-medium">
                          {req.id}
                        </div>
                        <h2 className="text-white font-medium text-base mt-1 group-hover:text-cyan-300 transition-colors">
                          {req.title}
                        </h2>
                        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-white/45 font-sans">
                          <span>Người yêu cầu: {req.requester}</span>
                          <span>•</span>
                          <span>Phòng: {req.department}</span>
                          <span>•</span>
                          <span>Bắt đầu: {req.startDate}</span>
                        </div>
                      </div>

                      {/* Right Badges */}
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-md ${priorityMeta.classNames}`}>
                          {priorityMeta.label}
                        </span>

                        <span
                          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium`}
                        >
                          <span className={`size-1.5 rounded-full ${statusMeta.dotClass}`} />
                          <span>{statusMeta.label}</span>
                        </span>

                        <ChevronRight
                          size={16}
                          className="text-white/25 group-hover:text-cyan-300 group-hover:translate-x-0.5 transition-all ml-1"
                        />
                      </div>
                    </div>

                    {/* Row 2: Fulfillment Progress */}
                    <div className="mt-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-white/45">Hoàn thành</span>
                        <span className="font-mono text-white/70 font-medium">
                          {completedTasks}/{totalTasks} TASKS
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="mt-2 h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all duration-700"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>

                      {/* Sub-task Chips */}
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {req.tasks.map((task) => {
                          const tMeta = TASK_STATUS_META[task.status];
                          const TaskIcon = tMeta.icon;

                          return (
                            <div
                              key={task.id}
                              className={`rounded-md border px-2 py-1 text-[10px] inline-flex items-center gap-1.5 font-sans ${tMeta.borderClass} ${tMeta.bgClass} ${tMeta.textClass}`}
                            >
                              <TaskIcon
                                size={12}
                                className={task.status === 'IN_PROGRESS' ? 'animate-spin' : ''}
                              />
                              <span>{task.name}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Row 3: Assignee Footer */}
                    <div className="pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-2 text-xs text-white/35">
                      <div className="flex items-center gap-1.5">
                        <UserRound size={12} className="text-white/40" />
                        <span>Giao cho: {req.assignee}</span>
                      </div>
                      <span>Cập nhật: {req.updatedAt}</span>
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
              <PackageCheck size={40} className="text-white/20 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Không có request nào cần xử lý</p>
              <p className="mt-1 text-sm text-white/45">Các request mới được giao sẽ hiện ở đây.</p>
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="mt-5 rounded-xl border border-white/10 bg-white/[0.05] px-5 py-2.5 text-sm text-white/70 hover:text-white transition cursor-pointer inline-flex items-center gap-2"
              >
                <RefreshCw size={14} />
                <span>Làm mới</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
