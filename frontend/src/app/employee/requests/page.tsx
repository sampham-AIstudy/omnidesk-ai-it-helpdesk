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
  Clock3,
  XCircle,
} from 'lucide-react';
import {
  STATUS_META,
  PRIORITY_META,
  STATUS_SEQUENCE,
  StatusKey,
  ServiceRequest,
} from '@/lib/serviceRequestsData';
import api from '@/lib/api';
import { formatVietnamTime } from '@/lib/utils';

const API_STATUS_TO_UI: Record<string, StatusKey> = {
  submitted: 'SUBMITTED', pending_approval: 'MANAGER_APPROVAL', approved: 'IT_APPROVAL',
  assigned: 'FULFILLMENT', in_progress: 'FULFILLMENT', waiting_for_user: 'PROVISIONING',
  fulfilled: 'COMPLETED', closed: 'COMPLETED', rejected: 'REJECTED', cancelled: 'REJECTED',
};

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
} as const;

export default function ServiceRequestsListPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [liveRequests, setLiveRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    document.title = 'My Service Requests — Yêu Cầu Của Tôi';
  }, []);

  useEffect(() => {
    let active = true;
    api.get('/service-requests/mine').then(({ data }) => {
      if (!active) return;
      setLiveRequests(data.items.map((item: { request_number: string; service_name: string; category: string; status: string; risk_level: string; created_at: string; fulfillment_group: string; approved_at?: string | null }) => {
        const status = item.approved_at && item.status === 'submitted' ? 'IT_APPROVAL' : (API_STATUS_TO_UI[item.status] || 'SUBMITTED');
        return {
          id: item.request_number, title: item.service_name, category: item.category, status,
          priority: item.risk_level === 'high' ? 'P1' : item.risk_level === 'medium' ? 'P2' : 'P3',
          createdAt: formatVietnamTime(item.created_at), requester: 'Bạn',
          department: 'Theo hồ sơ nhân sự', costCenter: 'N/A', description: 'Service Request được tạo từ IT Service Catalog.',
          items: [{ id: `FL-${item.request_number}`, name: item.service_name, status, assignee: item.fulfillment_group, updatedAt: formatVietnamTime(item.created_at) }], timeline: [],
        };
      }));
    }).catch(() => {
      if (active) setLoadError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const allRequests = useMemo(() => liveRequests, [liveRequests]);

  const filteredRequests = useMemo(() => {
    return allRequests.filter((req) => {
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
  }, [allRequests, searchQuery, statusFilter, priorityFilter]);

  const handleCardClick = (id: string) => {
    router.push(`/employee/requests/${id}`);
  };

  const requestSummary = useMemo(() => ({
    total: allRequests.length,
    active: allRequests.filter((request) => !['COMPLETED', 'REJECTED'].includes(request.status)).length,
    completed: allRequests.filter((request) => request.status === 'COMPLETED').length,
    rejected: allRequests.filter((request) => request.status === 'REJECTED').length,
  }), [allRequests]);

  const getProgressPercentage = (status: StatusKey) => {
    if (status === 'REJECTED') return 100;
    const index = STATUS_SEQUENCE.indexOf(status);
    if (index === -1) return 0;
    return Math.round((index / (STATUS_SEQUENCE.length - 1)) * 100);
  };

  return (
    <div className="min-h-screen bg-light-mesh text-slate-900 selection:bg-blue-100 selection:text-blue-900 p-6 lg:p-10 relative overflow-hidden font-sans rounded-2xl">

      {/* HEADER */}
      <header className="pt-2 pb-8 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-blue-700 transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-slate-700">My Service Requests</span>
        </div>

        {/* Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-slate-900 tracking-tight">
              My Service Requests{' '}
              <span className="text-blue-700">Yêu Cầu Của Tôi</span>
            </h1>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed max-w-2xl">
              Theo dõi các yêu cầu dịch vụ (Service Request) — khác với Incident, mỗi request là một đơn xin sản phẩm/dịch vụ đi qua workflow phê duyệt & fulfillment.
            </p>
          </div>

          <div className="shrink-0">
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-slate-500 flex items-center gap-2 rounded-full border border-slate-200 bg-white/75 px-4 py-2 backdrop-blur">
              <span className={`size-2 rounded-full ${loadError ? 'bg-red-400' : loading ? 'bg-amber-400' : 'bg-emerald-500'}`} />
              <span>{loadError ? 'KHÔNG THỂ TẢI' : loading ? 'ĐANG TẢI' : 'DỮ LIỆU MÁY CHỦ'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation already separates incidents from requests. */}
      <div className="hidden">
        <div className="grid grid-cols-2 gap-2 w-full max-w-sm rounded-2xl border border-slate-200 bg-white/75 p-1.5 backdrop-blur-md shadow-sm">
          {/* Tab 1: Incidents Link */}
          <Link
            href="/employee/tickets"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-transparent bg-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-all text-center"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <LifeBuoy size={16} />
              <span>My Incidents</span>
            </div>
            <span className="font-mono text-[9px] text-slate-400 mt-0.5">INC · Sự cố</span>
          </Link>

          {/* Tab 2: Requests (Active) */}
          <button
            type="button"
            className="relative flex flex-col items-center justify-center py-2.5 px-3 rounded-xl border border-blue-200 bg-blue-50 text-blue-700 font-semibold transition-all text-center cursor-pointer shadow-sm"
          >
            <div className="flex items-center gap-1.5 font-medium text-xs">
              <Package size={16} />
              <span>My Requests</span>
            </div>
            <span className="font-mono text-[9px] text-blue-600 mt-0.5">REQ · Dịch vụ</span>
            <motion.div
              layoutId="seg"
              className="h-0.5 bg-blue-600 absolute bottom-0 inset-x-4 rounded-full"
            />
          </button>
        </div>
      </div>

      <section className="relative z-10 mb-6 grid grid-cols-2 overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 shadow-sm sm:grid-cols-4">
        {[
          { label: 'Tổng yêu cầu', value: requestSummary.total, icon: Package, tone: 'text-slate-700' },
          { label: 'Đang xử lý', value: requestSummary.active, icon: Clock3, tone: 'text-blue-700' },
          { label: 'Hoàn tất', value: requestSummary.completed, icon: CheckCircle2, tone: 'text-emerald-700' },
          { label: 'Từ chối', value: requestSummary.rejected, icon: XCircle, tone: 'text-red-700' },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="border-b border-r border-slate-200 bg-white px-4 py-4 last:border-r-0 sm:border-b-0">
              <div className={`flex items-center gap-2 text-xs font-medium ${item.tone}`}><Icon size={15} />{item.label}</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{item.value}</div>
            </div>
          );
        })}
      </section>

      {loadError && <div className="relative z-10 mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">Không thể tải yêu cầu dịch vụ từ hệ thống. Dữ liệu minh họa không được hiển thị thay cho dữ liệu thật.</div>}

      {/* FILTER BAR */}
      <div className="mb-6 flex flex-col md:flex-row gap-3 relative z-10">
        {/* Search input */}
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo mã REQ hoặc tên dịch vụ..."
            className="w-full rounded-xl border border-slate-300 bg-white/90 py-3 pl-12 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition font-sans shadow-sm"
          />
        </div>

        {/* Status select */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-slate-300 bg-white/90 px-4 py-3 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 cursor-pointer shadow-sm"
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-white text-slate-900">
              {opt.label}
            </option>
          ))}
        </select>

        {/* Priority select */}
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="rounded-xl border border-slate-300 bg-white/90 px-4 py-3 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 cursor-pointer shadow-sm"
        >
          {PRIORITY_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-white text-slate-900">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* REQUEST LIST */}
      <div className="relative z-10">
        {loading && <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3" aria-label="Đang tải yêu cầu dịch vụ">{Array.from({ length: 3 }, (_, index) => <div key={index} className="h-64 rounded-2xl border border-slate-200 bg-white p-5"><div className="skeleton h-4 w-28" /><div className="mt-3 skeleton h-6 w-2/3" /><div className="mt-8 skeleton h-20 w-full" /></div>)}</div>}
        {!loading && (
        <AnimatePresence mode="wait">
          {filteredRequests.length > 0 ? (
            <motion.div
              key="list"
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid gap-4 xl:grid-cols-2"
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
                    className="group glass-card-light glass-card-light-hover rounded-2xl p-5 transition-all duration-300 cursor-pointer flex min-h-[252px] flex-col gap-4"
                  >
                    {/* Row 1: Request Info & Badges */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="font-mono text-[11px] tracking-[0.1em] text-blue-700 font-medium">
                          {req.id}
                        </div>
                        <h2 className="text-slate-900 font-medium text-base mt-1 group-hover:text-blue-700 transition-colors">
                          {req.title}
                        </h2>
                        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 font-sans">
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
                          className="text-slate-300 group-hover:text-blue-700 group-hover:translate-x-0.5 transition-all ml-1"
                        />
                      </div>
                    </div>

                    {/* Row 2: Progress Bar */}
                    <div className="hidden sm:block pt-1">
                      <div className="flex items-center justify-between mb-2 text-[11px] font-mono text-slate-500">
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
                                  <CheckCircle2 size={13} className="text-blue-600 animate-pulse" />
                                ) : (
                                  <Circle size={13} className="text-slate-300" />
                                )}
                                <span
                                  className={`text-[10px] ${
                                    isDone
                                       ? 'text-slate-700'
                                      : isCurrent
                                       ? 'text-blue-700 font-semibold'
                                       : 'text-slate-400'
                                  }`}
                                >
                                  {STATUS_META[stKey].label}
                                </span>
                                {idx < STATUS_SEQUENCE.length - 1 && (
                                  <span className="text-slate-300 ml-1">•</span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        <span>{progressPct}%</span>
                      </div>

                      {/* Thin Progress line */}
                      <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 transition-all duration-500 rounded-full"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Row 3: Item Chips */}
                    <div className="pt-2 border-t border-slate-200 flex flex-wrap gap-2">
                      {req.items.map((item) => {
                        const itemStatusMeta = STATUS_META[item.status];
                        return (
                          <div
                            key={item.id}
                            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] text-slate-600 inline-flex items-center gap-1.5 font-sans"
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
              className="py-20 text-center flex flex-col items-center justify-center rounded-3xl border border-slate-200 bg-white/75 shadow-sm"
            >
              <PackageOpen size={40} className="text-slate-300 mx-auto" />
              <p className="mt-4 text-slate-800 font-medium text-base">Chưa có yêu cầu dịch vụ nào</p>
              <p className="mt-1 text-sm text-slate-500">Bấm &apos;Yêu Cầu Dịch Vụ&apos; để tạo request đầu tiên.</p>
              <Link
                href="/employee/catalog"
                className="mt-5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition cursor-pointer inline-flex items-center gap-2"
              >
                <span>Tạo Yêu Cầu Mới</span>
                <ChevronRight size={16} />
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
        )}
      </div>
    </div>
  );
}
