'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ArrowLeft,
  CalendarDays,
  UserRound,
  Users,
  Building2,
  GitPullRequest,
  PackageOpen,
  Check,
  Circle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import {
  MOCK_REQUESTS,
  STATUS_META,
  PRIORITY_META,
  STATUS_SEQUENCE,
  ServiceRequest,
  StatusKey,
} from '@/lib/serviceRequestsData';

export default function ServiceRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reqId = params?.id as string;

  const [request, setRequest] = useState<ServiceRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    setLoading(true);
    // Simulate API fetch / lookup
    const found = MOCK_REQUESTS.find((r) => r.id === reqId);
    if (found) {
      setRequest(JSON.parse(JSON.stringify(found)));
      document.title = `Chi Tiết Yêu Cầu ${found.id}`;
    } else {
      setRequest(null);
    }
    setLoading(false);
  }, [reqId]);

  const handleCancelRequest = () => {
    if (!request) return;
    setCancelling(true);
    setTimeout(() => {
      setRequest((prev) =>
        prev
          ? {
              ...prev,
              status: 'REJECTED',
              rejectionReason: 'Đã hủy bởi người dùng (Requester cancelled).',
            }
          : null
      );
      setCancelling(false);
      setShowCancelModal(false);
    }, 600);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex flex-col items-center justify-center rounded-3xl">
        <AlertTriangle size={48} className="text-amber-400 mb-4" />
        <h1 className="text-2xl font-bold">Không tìm thấy yêu cầu</h1>
        <p className="text-white/50 text-sm mt-1">Mã yêu cầu "{reqId}" không tồn tại hoặc đã bị xóa.</p>
        <Link
          href="/employee/requests"
          className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition"
        >
          <ArrowLeft size={16} />
          <span>Quay lại danh sách</span>
        </Link>
      </div>
    );
  }

  const statusMeta = STATUS_META[request.status];
  const priorityMeta = PRIORITY_META[request.priority];
  const StatusIcon = statusMeta.icon;
  const isRejected = request.status === 'REJECTED';
  const currentStepIdx = isRejected ? -1 : STATUS_SEQUENCE.indexOf(request.status);
  const canCancel = request.status === 'SUBMITTED' || request.status === 'MANAGER_APPROVAL';

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <Link href="/employee/requests" className="hover:text-white transition-colors">
            My Service Requests
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-cyan-300 font-mono font-medium">{request.id}</span>
        </div>

        {/* Back Link */}
        <div className="mt-4">
          <Link
            href="/employee/requests"
            className="inline-flex items-center gap-2 text-xs text-white/60 hover:text-white transition-colors"
          >
            <ArrowLeft size={16} />
            <span>Quay lại danh sách</span>
          </Link>
        </div>
      </header>

      {/* REJECTED BANNER (If status === REJECTED) */}
      {isRejected && (
        <div className="mb-6 rounded-2xl border border-red-400/30 bg-red-400/10 px-5 py-4 flex items-start gap-3.5 relative z-10 backdrop-blur-md">
          <XCircle size={20} className="text-red-300 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-red-200 font-semibold">Yêu cầu đã bị từ chối</p>
            <p className="text-xs text-red-300/80 mt-1 leading-relaxed">
              Lý do: {request.rejectionReason || 'Không đủ điều kiện phê duyệt.'}
            </p>
            <div className="mt-3">
              <Link
                href="/employee/catalog"
                className="rounded-lg border border-red-400/40 bg-red-400/10 hover:bg-red-400/20 px-4 py-2 text-xs text-red-200 font-medium transition inline-flex items-center gap-1.5"
              >
                <span>Gửi yêu cầu mới</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* TOP CARD */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 relative z-10">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/80 font-medium">
              {request.id}
            </div>
            <h1 className="mt-2 text-2xl xl:text-3xl font-semibold text-white tracking-tight">
              {request.title}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-white/55 max-w-2xl">
              {request.description}
            </p>
          </div>

          {/* Right column chips & actions */}
          <div className="flex flex-col items-start lg:items-end gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 text-xs font-semibold rounded-md ${priorityMeta.classNames}`}>
                {priorityMeta.label}
              </span>
              <span
                className={`flex items-center gap-2 text-sm px-4 py-2 rounded-xl border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium shadow-sm`}
              >
                <StatusIcon size={16} />
                <span>{statusMeta.label}</span>
              </span>
            </div>

            {/* Cancel Request Button */}
            {canCancel && (
              <button
                type="button"
                onClick={() => setShowCancelModal(true)}
                className="mt-1 rounded-xl border border-red-400/40 bg-red-400/10 hover:bg-red-400/20 px-4 py-2 text-xs text-red-300 font-medium transition cursor-pointer"
              >
                Hủy yêu cầu
              </button>
            )}
          </div>
        </div>

        {/* Meta Grid (4 Tiles) */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 border-t border-white/10">
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <CalendarDays size={16} className="text-cyan-300" />
              <span>Ngày tạo</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{request.createdAt}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <UserRound size={16} className="text-cyan-300" />
              <span>Người yêu cầu</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{request.requester}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <Users size={16} className="text-cyan-300" />
              <span>Phòng ban</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{request.department}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <Building2 size={16} className="text-cyan-300" />
              <span>Cost Center</span>
            </div>
            <div className="text-sm text-white/80 font-mono font-medium truncate">{request.costCenter}</div>
          </div>
        </div>
      </div>

      {/* BODY GRID: Timeline & Items */}
      <div className="mt-6 grid lg:grid-cols-[1.15fr_1fr] gap-6 relative z-10">
        {/* LEFT COLUMN — REQUEST TIMELINE */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <GitPullRequest size={18} className="text-cyan-300" />
              <span>Timeline Xử Lý</span>
            </h2>

            {/* Vertical timeline */}
            <div className="mt-6 relative pl-2">
              {/* Vertical connecting line */}
              <div className="absolute left-[19px] top-3 bottom-3 w-px bg-white/10 pointer-events-none" />

              <div className="space-y-6">
                {request.timeline.map((step, idx) => {
                  const stepMeta = STATUS_META[step.key];
                  const isDone = isRejected ? false : currentStepIdx > idx || request.status === 'COMPLETED';
                  const isCurrent = isRejected ? false : currentStepIdx === idx;
                  const isStepRejected = isRejected && idx === Math.max(0, currentStepIdx);

                  return (
                    <div key={step.key} className={`relative flex gap-4 ${isRejected && idx > 2 ? 'opacity-40' : ''}`}>
                      {/* Step Node Icon */}
                      <div className="relative z-10 shrink-0">
                        {isStepRejected ? (
                          <div className="size-10 rounded-full border border-red-400 bg-red-400/20 text-red-400 flex items-center justify-center shadow-md">
                            <XCircle size={18} />
                          </div>
                        ) : isDone ? (
                          <div className="size-10 rounded-full bg-emerald-400 text-black flex items-center justify-center font-bold shadow-md">
                            <Check size={18} strokeWidth={3} />
                          </div>
                        ) : isCurrent ? (
                          <div className="relative size-10 rounded-full border-2 border-cyan-400 bg-cyan-400/10 text-cyan-300 flex items-center justify-center font-bold shadow-md shadow-cyan-500/20">
                            <span className="absolute inset-0 rounded-full ring-2 ring-cyan-400/40 animate-ping" />
                            <span className="text-xs font-mono">{idx + 1}</span>
                          </div>
                        ) : (
                          <div className="size-10 rounded-full border border-white/10 bg-white/[0.03] text-white/30 flex items-center justify-center font-mono text-xs">
                            {idx + 1}
                          </div>
                        )}
                      </div>

                      {/* Step Content */}
                      <div className="pt-1.5 flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3
                            className={`text-sm font-medium ${
                              isCurrent ? 'text-cyan-300 font-semibold' : isDone ? 'text-white' : 'text-white/50'
                            }`}
                          >
                            {step.title} <span className="text-xs text-white/40 font-normal">({step.subTitle})</span>
                          </h3>
                          {step.doneAt && (
                            <span className="font-mono text-[10px] text-white/35 shrink-0">{step.doneAt}</span>
                          )}
                        </div>

                        {/* Step Note */}
                        {step.note && (
                          <p
                            className={`text-xs mt-1 leading-relaxed ${
                              isCurrent ? 'text-cyan-300/90 font-medium' : 'text-white/50'
                            }`}
                          >
                            {step.note}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN — FULFILLMENT ITEMS */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <PackageOpen size={18} className="text-cyan-300" />
              <span>Fulfillment Items</span>
            </h2>
            <span className="font-mono text-[10px] text-white/40 border border-white/10 rounded-full px-2.5 py-0.5">
              {request.items.length} ITEMS
            </span>
          </div>

          <p className="text-xs text-white/45 mt-1.5">
            Mỗi request có thể chứa nhiều hạng mục cấp phát, theo dõi riêng từng item.
          </p>

          {/* Item Cards List */}
          <div className="mt-5 space-y-3">
            {request.items.map((item) => {
              const itemStatusMeta = STATUS_META[item.status];
              const ItemStatusIcon = itemStatusMeta.icon;

              return (
                <div
                  key={item.id}
                  className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 hover:border-white/20 transition-all"
                >
                  {/* Row 1: ID & Status */}
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-cyan-300/70">{item.id}</span>
                    <span
                      className={`flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full border ${itemStatusMeta.borderClass} ${itemStatusMeta.bgClass} ${itemStatusMeta.textClass} font-medium`}
                    >
                      <ItemStatusIcon size={12} />
                      <span>{itemStatusMeta.label}</span>
                    </span>
                  </div>

                  {/* Row 2: Item Name & Assignee */}
                  <h3 className="text-sm font-medium text-white mt-2">{item.name}</h3>
                  {item.assignee && (
                    <div className="text-xs text-white/45 mt-1 flex items-center gap-1.5">
                      <UserRound size={12} className="text-white/40" />
                      <span>Giao cho: {item.assignee}</span>
                    </div>
                  )}

                  {/* Row 3: Sub-task Chips */}
                  {item.subTasks && item.subTasks.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap gap-1.5">
                      {item.subTasks.map((st) => (
                        <div
                          key={st.id}
                          className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] text-white/50 inline-flex items-center gap-1.5"
                        >
                          {st.completed ? (
                            <CheckCircle2 size={12} className="text-cyan-400" />
                          ) : (
                            <Circle size={12} className="text-white/20" />
                          )}
                          <span>{st.title}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Row 4: Updated At Footer */}
                  <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between text-xs text-white/35">
                    <span>Cập nhật: {item.updatedAt}</span>
                    <span className="text-cyan-300/70 hover:text-cyan-300 font-medium inline-flex items-center gap-1 cursor-pointer">
                      <span>Chi tiết</span>
                      <ArrowRight size={12} />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* CANCEL CONFIRMATION MODAL */}
      <AnimatePresence>
        {showCancelModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-red-400/30 bg-[#0f1422] p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3 text-red-300">
                <AlertTriangle size={24} />
                <h3 className="text-lg font-semibold text-white">Hủy yêu cầu dịch vụ?</h3>
              </div>
              <p className="text-sm text-white/60 leading-relaxed">
                Bạn có chắc chắn muốn hủy yêu cầu <span className="font-mono text-cyan-300">{request.id}</span> không? Thao tác này sẽ dừng toàn bộ quy trình phê duyệt & cấp phát.
              </p>
              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCancelModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white text-xs font-medium transition cursor-pointer"
                >
                  Không
                </button>
                <button
                  type="button"
                  onClick={handleCancelRequest}
                  disabled={cancelling}
                  className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-semibold transition cursor-pointer inline-flex items-center gap-1.5 disabled:opacity-50"
                >
                  {cancelling ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>Đang hủy...</span>
                    </>
                  ) : (
                    <span>Hủy yêu cầu</span>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
