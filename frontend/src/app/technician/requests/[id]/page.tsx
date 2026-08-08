'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  ArrowLeft,
  CalendarDays,
  UserRound,
  Users,
  Building2,
  ListChecks,
  CheckCheck,
  Zap,
  History,
  OctagonAlert,
  Loader2,
  Check,
  Circle,
  GitBranch,
  GitMerge,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import {
  MOCK_WORKBENCH_REQUESTS,
  TASK_STATUS_META,
  PRIORITY_META,
  deriveRequestStatus,
  RequestFulfillment,
  FulfillmentTask,
  TaskStatus,
} from '@/lib/fulfillmentData';

export default function FulfillmentDetailWorkbenchPage() {
  const params = useParams();
  const router = useRouter();
  const reqId = params?.id as string;

  const [reqData, setReqData] = useState<RequestFulfillment | null>(null);
  const [loading, setLoading] = useState(true);
  const [notesState, setNotesState] = useState<Record<string, string>>({});
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [targetBlockTaskId, setTargetBlockTaskId] = useState<string | null>(null);
  const [blockReasonInput, setBlockReasonInput] = useState('');
  const [completedBanner, setCompletedBanner] = useState(false);

  useEffect(() => {
    setLoading(true);
    const found = MOCK_WORKBENCH_REQUESTS.find((r) => r.id === reqId);
    if (found) {
      const cloned: RequestFulfillment = JSON.parse(JSON.stringify(found));
      setReqData(cloned);
      document.title = `Chi Tiết Fulfillment ${cloned.id}`;

      // Initialize notes state
      const notesMap: Record<string, string> = {};
      cloned.tasks.forEach((t) => {
        if (t.notes) notesMap[t.id] = t.notes;
      });
      setNotesState(notesMap);
    } else {
      setReqData(null);
    }
    setLoading(false);
  }, [reqId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!reqData) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex flex-col items-center justify-center rounded-3xl">
        <AlertTriangle size={48} className="text-amber-400 mb-4" />
        <h1 className="text-2xl font-bold">Không tìm thấy yêu cầu</h1>
        <p className="text-white/50 text-sm mt-1">Mã yêu cầu "{reqId}" không tồn tại hoặc đã bị gỡ.</p>
        <Link
          href="/technician/requests"
          className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition"
        >
          <ArrowLeft size={16} />
          <span>Quay lại Workbench</span>
        </Link>
      </div>
    );
  }

  const derivedStatus = deriveRequestStatus(reqData.tasks);
  const statusMeta = TASK_STATUS_META[derivedStatus];
  const priorityMeta = PRIORITY_META[reqData.priority];
  const StatusIcon = statusMeta.icon;

  const completedCount = reqData.tasks.filter((t) => t.status === 'COMPLETED').length;
  const totalCount = reqData.tasks.length;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const isAllTasksCompleted = completedCount === totalCount;

  // Toggle task status with dependency check
  const handleTaskCheckboxClick = (task: FulfillmentTask) => {
    // Dependency check
    if (task.dependsOn && task.dependsOn.length > 0) {
      const pendingDeps = task.dependsOn.filter((depId) => {
        const depTask = reqData.tasks.find((t) => t.id === depId);
        return depTask && depTask.status !== 'COMPLETED';
      });

      if (pendingDeps.length > 0) {
        toast.error('Hoàn thành task phụ thuộc trước!');
        return;
      }
    }

    let nextStatus: TaskStatus = 'COMPLETED';
    if (task.status === 'PENDING') nextStatus = 'IN_PROGRESS';
    else if (task.status === 'IN_PROGRESS') nextStatus = 'COMPLETED';
    else if (task.status === 'COMPLETED') nextStatus = 'IN_PROGRESS';
    else if (task.status === 'BLOCKED') nextStatus = 'IN_PROGRESS';

    setReqData((prev) => {
      if (!prev) return null;
      const updatedTasks = prev.tasks.map((t) =>
        t.id === task.id ? { ...t, status: nextStatus, blockedReason: undefined } : t
      );
      const newActivity = {
        id: `act-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        actor: 'Lê Minh Công',
        message: `đã chuyển "${task.name}" sang ${TASK_STATUS_META[nextStatus].label}.`,
        statusColor: TASK_STATUS_META[nextStatus].color,
      };

      return {
        ...prev,
        updatedAt: 'Vừa xong',
        tasks: updatedTasks,
        activities: [newActivity, ...prev.activities],
      };
    });

    toast.success(`Đã cập nhật: ${task.name} → ${TASK_STATUS_META[nextStatus].label}`);
  };

  const handleSaveNote = (taskId: string) => {
    const noteText = notesState[taskId] || '';
    setReqData((prev) => {
      if (!prev) return null;
      const updatedTasks = prev.tasks.map((t) =>
        t.id === taskId ? { ...t, notes: noteText } : t
      );
      return { ...prev, tasks: updatedTasks };
    });
    toast.success('Đã lưu ghi chú kết quả!');
  };

  const handleUnblockTask = (taskId: string) => {
    setReqData((prev) => {
      if (!prev) return null;
      const updatedTasks = prev.tasks.map((t) =>
        t.id === taskId ? { ...t, status: 'IN_PROGRESS' as TaskStatus, blockedReason: undefined } : t
      );
      return { ...prev, tasks: updatedTasks };
    });
    toast.success('Đã gỡ chặn task!');
  };

  const handleOpenBlockModal = (taskId?: string) => {
    setTargetBlockTaskId(taskId || reqData.tasks.find((t) => t.status === 'IN_PROGRESS')?.id || reqData.tasks[0]?.id);
    setBlockReasonInput('');
    setShowBlockModal(true);
  };

  const handleConfirmBlock = () => {
    if (!targetBlockTaskId || !blockReasonInput.trim()) {
      toast.error('Vui lòng nhập lý do bị chặn.');
      return;
    }

    setReqData((prev) => {
      if (!prev) return null;
      const updatedTasks = prev.tasks.map((t) =>
        t.id === targetBlockTaskId ? { ...t, status: 'BLOCKED' as TaskStatus, blockedReason: blockReasonInput } : t
      );
      const newActivity = {
        id: `act-${Date.now()}`,
        timestamp: 'Vừa xong',
        actor: 'Lê Minh Công',
        message: `đã đánh dấu task bị chặn: "${blockReasonInput}"`,
        statusColor: '#f87171',
      };

      return {
        ...prev,
        tasks: updatedTasks,
        activities: [newActivity, ...prev.activities],
      };
    });

    setShowBlockModal(false);
    toast.error('Đã cập nhật trạng thái Bị chặn.');
  };

  const handleCompleteAll = () => {
    setReqData((prev) => {
      if (!prev) return null;
      const updatedTasks = prev.tasks.map((t) => ({ ...t, status: 'COMPLETED' as TaskStatus }));
      return { ...prev, tasks: updatedTasks };
    });
    setCompletedBanner(true);
    toast.success(`Yêu cầu ${reqData.id} đã hoàn tất toàn bộ!`);
  };

  // Group tasks by order phase
  const group1Sequential = reqData.tasks.filter((t) => t.order === 1 || (t.order === 2 && !t.parallel));
  const group2Parallel = reqData.tasks.filter((t) => t.parallel);
  const group3Sequential = reqData.tasks.filter((t) => t.order >= 4 && !t.parallel);

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/technician/queue" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <Link href="/technician/requests" className="hover:text-white transition-colors">
            Fulfillment Workbench
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-cyan-300 font-mono font-medium">{reqData.id}</span>
        </div>

        {/* Back Link */}
        <div className="mt-4">
          <Link
            href="/technician/requests"
            className="inline-flex items-center gap-2 text-xs text-white/60 hover:text-white transition-colors"
          >
            <ArrowLeft size={16} />
            <span>Quay lại Workbench</span>
          </Link>
        </div>
      </header>

      {/* COMPLETED SUCCESS BANNER */}
      {completedBanner && (
        <div className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-4 flex items-center justify-between gap-4 relative z-10 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={24} className="text-emerald-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-200">
                Yêu cầu {reqData.id} đã hoàn tất và bàn giao thành công!
              </p>
              <p className="text-xs text-emerald-300/80 mt-0.5">
                Tất cả {totalCount} fulfillment tasks đã hoàn thành. Hệ thống đã tự động gửi email thông báo bàn giao.
              </p>
            </div>
          </div>
          <Link
            href="/technician/requests"
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-bold transition shrink-0"
          >
            Về Workbench
          </Link>
        </div>
      )}

      {/* REQUEST INFO CARD */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 relative z-10">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/80 font-medium">
              {reqData.id}
            </div>
            <h1 className="mt-2 text-2xl xl:text-3xl font-semibold text-white tracking-tight">
              {reqData.title}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-white/55 max-w-2xl">
              {reqData.description}
            </p>
          </div>

          {/* Right column chips */}
          <div className="flex flex-col items-start lg:items-end gap-2.5 shrink-0">
            <span className={`px-2.5 py-1 text-xs font-semibold rounded-md ${priorityMeta.classNames}`}>
              {priorityMeta.label}
            </span>
            <span
              className={`flex items-center gap-2 text-sm px-4 py-2 rounded-xl border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium shadow-sm`}
            >
              <StatusIcon size={16} className={derivedStatus === 'IN_PROGRESS' ? 'animate-spin' : ''} />
              <span>{statusMeta.label}</span>
            </span>
          </div>
        </div>

        {/* Meta Grid (4 Tiles) */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 border-t border-white/10">
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <CalendarDays size={16} className="text-cyan-300" />
              <span>Ngày bắt đầu</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{reqData.startDate}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <UserRound size={16} className="text-cyan-300" />
              <span>Người yêu cầu</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{reqData.requester}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <Users size={16} className="text-cyan-300" />
              <span>Phòng ban</span>
            </div>
            <div className="text-sm text-white/80 font-medium truncate">{reqData.department}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-white/45">
              <Building2 size={16} className="text-cyan-300" />
              <span>Cost Center</span>
            </div>
            <div className="text-sm text-white/80 font-mono font-medium truncate">{reqData.costCenter}</div>
          </div>
        </div>

        {/* Overall Progress Footer */}
        <div className="mt-5 pt-4 border-t border-white/10 flex items-center gap-4">
          <span className="text-xs text-white/45 shrink-0">Tiến độ chung</span>
          <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <span className="font-mono text-xs text-white/70 font-medium shrink-0">
            {completedCount}/{totalCount} TASKS
          </span>
        </div>
      </div>

      {/* FULFILLMENT WORKSPACE GRID */}
      <div className="mt-6 grid lg:grid-cols-[1fr_320px] gap-6 relative z-10">
        {/* LEFT COLUMN — TASK LIST (PHASE GROUPED) */}
        <section className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <ListChecks size={18} className="text-cyan-300" />
                <span>Fulfillment Tasks</span>
              </h2>
              <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/35">
                3 SEQUENTIAL · 2 PARALLEL
              </span>
            </div>

            {/* PHASE 1: SEQUENTIAL */}
            {group1Sequential.length > 0 && (
              <div className="mt-6">
                <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/35 mb-3 flex items-center gap-2">
                  <span>BƯỚC 1 · TUẦN TỰ</span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>
                <div className="space-y-3">
                  {group1Sequential.map((t) => renderTaskCard(t))}
                </div>
              </div>
            )}

            {/* PHASE 2: PARALLEL */}
            {group2Parallel.length > 0 && (
              <div className="mt-6">
                <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-cyan-300/80 mb-3 flex items-center gap-2">
                  <span className="flex items-center gap-1.5">
                    <GitBranch size={13} className="text-cyan-300" />
                    <span>BƯỚC 2 · SONG SONG</span>
                  </span>
                  <div className="h-px flex-1 bg-cyan-400/20" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {group2Parallel.map((t) => renderTaskCard(t, true))}
                </div>
              </div>
            )}

            {/* PHASE 3: SEQUENTIAL */}
            {group3Sequential.length > 0 && (
              <div className="mt-6">
                <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/35 mb-3 flex items-center gap-2">
                  <span>BƯỚC 3 · TUẦN TỰ</span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>
                <div className="space-y-3">
                  {group3Sequential.map((t) => renderTaskCard(t))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* RIGHT SIDE PANEL */}
        <section className="space-y-5">
          {/* Card 1: Request Actions */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap size={16} className="text-cyan-300" />
              <span>Thao Tác</span>
            </h3>

            <button
              type="button"
              onClick={handleCompleteAll}
              disabled={!isAllTasksCompleted}
              className="mt-4 w-full rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-blue-500 active:scale-[0.98] transition flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <CheckCheck size={16} />
              <span>Hoàn Tất Toàn Bộ</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenBlockModal()}
              className="mt-2.5 w-full rounded-xl border border-red-400/40 bg-red-400/[0.06] px-4 py-3 text-sm font-medium text-red-300 hover:bg-red-400/10 transition cursor-pointer flex items-center justify-center gap-2"
            >
              <OctagonAlert size={16} />
              <span>Đánh Dấu Bị Chặn</span>
            </button>
          </div>

          {/* Card 2: Activity Log */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
              <History size={16} className="text-cyan-300" />
              <span>Lịch Sử Thao Tác</span>
            </h3>

            <ul className="space-y-3.5 relative pl-3">
              <div className="absolute left-[6px] top-1.5 bottom-1.5 w-px bg-white/10" />

              {reqData.activities.map((act) => (
                <li key={act.id} className="relative flex gap-2.5 text-xs">
                  <span
                    className="size-2 rounded-full shrink-0 mt-1"
                    style={{ backgroundColor: act.statusColor || '#22d3ee' }}
                  />
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="font-mono text-[10px] text-white/35">{act.timestamp}</span>
                    <p className="text-white/70 leading-relaxed">
                      <strong className="text-white font-medium">{act.actor}</strong> {act.message}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>

      {/* BLOCKED REASON MODAL */}
      <AnimatePresence>
        {showBlockModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-red-400/30 bg-[#0f1422] p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3 text-red-300">
                <OctagonAlert size={24} />
                <h3 className="text-lg font-semibold text-white">Đánh dấu bị chặn?</h3>
              </div>

              <div>
                <label className="block mb-1.5 text-xs text-white/60">Lý do bị chặn / Đơn vị phục thuộc</label>
                <textarea
                  value={blockReasonInput}
                  onChange={(e) => setBlockReasonInput(e.target.value)}
                  placeholder="Ví dụ: Chờ bên Mua sắm giao thêm thiết bị kho, chờ phê duyệt bổ sung..."
                  rows={3}
                  className="w-full rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-white placeholder:text-white/25 focus:border-red-400/60 focus:outline-none focus:ring-2 focus:ring-red-400/20 transition resize-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowBlockModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white text-xs font-medium transition cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleConfirmBlock}
                  className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-semibold transition cursor-pointer"
                >
                  Xác nhận chặn
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );

  // Helper render Task Card
  function renderTaskCard(task: FulfillmentTask, isParallelBadge = false) {
    const tMeta = TASK_STATUS_META[task.status];
    const TaskIcon = tMeta.icon;

    let borderClass = 'border-white/10';
    let bgClass = 'bg-white/[0.02]';
    if (task.status === 'COMPLETED') {
      borderClass = 'border-emerald-400/30';
      bgClass = 'bg-emerald-400/[0.04]';
    } else if (task.status === 'IN_PROGRESS') {
      borderClass = 'border-cyan-400/50 ring-1 ring-cyan-400/20';
      bgClass = 'bg-cyan-400/[0.05]';
    } else if (task.status === 'BLOCKED') {
      borderClass = 'border-red-400/40';
      bgClass = 'bg-red-400/[0.04]';
    }

    return (
      <div
        key={task.id}
        className={`rounded-2xl border ${borderClass} ${bgClass} p-4 transition-all duration-300 relative flex flex-col justify-between`}
      >
        <div>
          {/* Row 1: Checkbox + Meta + Status */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              {/* Custom Checkbox Button */}
              <button
                type="button"
                onClick={() => handleTaskCheckboxClick(task)}
                className={`size-6 rounded-md border flex items-center justify-center shrink-0 transition-all duration-200 cursor-pointer mt-0.5 ${
                  task.status === 'COMPLETED'
                    ? 'bg-emerald-400 border-transparent text-black shadow-xs'
                    : task.status === 'IN_PROGRESS'
                    ? 'border-cyan-400 bg-cyan-400/10 text-cyan-300'
                    : task.status === 'BLOCKED'
                    ? 'border-red-400 bg-red-400/10 text-red-300'
                    : 'border-white/20 text-transparent hover:border-cyan-400/60 hover:bg-cyan-400/10 hover:text-cyan-300'
                }`}
              >
                {task.status === 'COMPLETED' && <Check size={14} strokeWidth={3} />}
                {task.status === 'IN_PROGRESS' && <Loader2 size={14} className="animate-spin" />}
                {task.status === 'BLOCKED' && <OctagonAlert size={14} />}
                {task.status === 'PENDING' && <Check size={14} />}
              </button>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-cyan-300/70">{task.id}</span>
                  {isParallelBadge && (
                    <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-300 bg-cyan-400/10 border border-cyan-400/20 px-1.5 py-0.5 rounded flex items-center gap-1">
                      <GitBranch size={10} />
                      <span>PARALLEL</span>
                    </span>
                  )}
                </div>
                <h4 className="text-sm font-medium text-white mt-0.5">{task.name}</h4>

                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-white/45">
                  {task.assignee && (
                    <span className="flex items-center gap-1">
                      <UserRound size={12} className="text-white/40" />
                      <span>{task.assignee}</span>
                    </span>
                  )}
                  {task.dueDate && (
                    <span className="flex items-center gap-1">
                      <Clock size={12} className="text-white/40" />
                      <span>Hạn: {task.dueDate}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Task Status Chip */}
            <span
              className={`flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full border ${tMeta.borderClass} ${tMeta.bgClass} ${tMeta.textClass} font-medium shrink-0`}
            >
              <TaskIcon size={12} className={task.status === 'IN_PROGRESS' ? 'animate-spin' : ''} />
              <span>{tMeta.label}</span>
            </span>
          </div>

          {/* Row 2: Dependency Chip */}
          {task.dependsOn && task.dependsOn.length > 0 && (
            <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center gap-1.5">
              <span className="rounded border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] text-white/45 inline-flex items-center gap-1 font-mono">
                <GitMerge size={10} />
                <span>Sau: {task.dependsOn.join(', ')}</span>
              </span>
            </div>
          )}
        </div>

        {/* Row 3: Notes Input (IN_PROGRESS or COMPLETED) */}
        {(task.status === 'IN_PROGRESS' || task.status === 'COMPLETED') && (
          <div className="mt-3 pt-2.5 border-t border-white/10 flex gap-2">
            <input
              type="text"
              value={notesState[task.id] || ''}
              onChange={(e) => setNotesState({ ...notesState, [task.id]: e.target.value })}
              placeholder="Ghi chú kết quả / URL, serial, mã license..."
              className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-1.5 text-xs text-white placeholder:text-white/25 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition font-sans"
            />
            <button
              type="button"
              onClick={() => handleSaveNote(task.id)}
              className="rounded-lg border border-white/10 bg-white/[0.05] hover:bg-white/10 px-3 py-1.5 text-xs text-white/70 hover:text-white transition cursor-pointer font-medium"
            >
              Lưu
            </button>
          </div>
        )}

        {/* Row 4: BLOCKED Reason & Unblock Action */}
        {task.status === 'BLOCKED' && (
          <div className="mt-3 pt-2.5 border-t border-red-400/20 flex items-center justify-between gap-2 text-xs text-red-300">
            <div className="flex items-center gap-1.5 min-w-0">
              <OctagonAlert size={12} className="shrink-0" />
              <span className="truncate">{task.blockedReason || 'Bị chặn bởi tác vụ phụ thuộc.'}</span>
            </div>
            <button
              type="button"
              onClick={() => handleUnblockTask(task.id)}
              className="text-red-300 hover:text-red-200 underline underline-offset-4 font-medium shrink-0 cursor-pointer"
            >
              Gỡ chặn
            </button>
          </div>
        )}
      </div>
    );
  }
}
