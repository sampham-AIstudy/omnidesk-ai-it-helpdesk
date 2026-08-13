'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
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
  ArrowRight,
} from 'lucide-react';
import {
  STATUS_META,
  PRIORITY_META,
  STATUS_SEQUENCE,
  ServiceRequest,
} from '@/lib/serviceRequestsData';
import api from '@/lib/api';
import { formatVietnamTime } from '@/lib/utils';

const API_STATUS_TO_UI = {
  submitted: 'SUBMITTED',
  pending_approval: 'MANAGER_APPROVAL',
  approved: 'IT_APPROVAL',
  assigned: 'FULFILLMENT',
  in_progress: 'FULFILLMENT',
  waiting_for_user: 'PROVISIONING',
  fulfilled: 'COMPLETED',
  closed: 'COMPLETED',
  rejected: 'REJECTED',
  cancelled: 'REJECTED',
} as const;

export default function ServiceRequestDetailPage() {
  const params = useParams();
  const reqId = params?.id as string;

  const [request, setRequest] = useState<ServiceRequest | null>(null);
  const [loadingRemote, setLoadingRemote] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;
    api.get(`/service-requests/${reqId}`).then(({ data }) => {
      if (!active) return;
      const fields = Object.entries(JSON.parse(data.form_data || '{}'))
        .filter(([, value]) => value)
        .map(([key, value]) => `${key}: ${value}`)
        .join('\n');
      const uiStatus = API_STATUS_TO_UI[data.status as keyof typeof API_STATUS_TO_UI] || 'SUBMITTED';
      setRequest({
        id: data.request_number,
        title: data.service_name,
        category: data.category,
        status: uiStatus,
        priority: data.risk_level === 'high' ? 'P1' : data.risk_level === 'medium' ? 'P2' : 'P3',
        createdAt: formatVietnamTime(data.created_at),
        requester: 'Bạn',
        department: 'Theo hồ sơ nhân sự',
        costCenter: 'N/A',
        description: fields || 'Không có thông tin bổ sung.',
        rejectionReason: data.rejection_reason || undefined,
        items: [{ id: `FL-${data.request_number}`, name: data.service_name, status: uiStatus, assignee: data.fulfillment_group, updatedAt: formatVietnamTime(data.updated_at) }],
        timeline: [
          { key: 'SUBMITTED', title: 'Submitted', subTitle: 'Đã gửi yêu cầu', doneAt: formatVietnamTime(data.created_at) },
          { key: 'MANAGER_APPROVAL', title: 'Approval', subTitle: 'Phê duyệt theo chính sách', note: data.approval_policy === '[]' ? 'Không yêu cầu phê duyệt.' : 'Đang chờ approval policy.' },
          { key: 'IT_APPROVAL', title: 'Routing', subTitle: 'Định tuyến fulfillment', note: `Nhóm xử lý: ${data.fulfillment_group}.` },
          { key: 'FULFILLMENT', title: 'Fulfillment', subTitle: 'Cấp phát dịch vụ' },
          { key: 'PROVISIONING', title: 'Provisioning', subTitle: 'Cấu hình / bàn giao' },
          { key: 'COMPLETED', title: 'Completed', subTitle: 'Hoàn tất & xác nhận' },
        ],
      });
    }).catch(() => {
      if (active) setLoadFailed(true);
    }).finally(() => { if (active) setLoadingRemote(false); });
    return () => { active = false; };
  }, [reqId]);

  useEffect(() => {
    if (request) document.title = `Chi Tiết Yêu Cầu ${request.id}`;
  }, [request]);

  if (loadingRemote) {
    return <div className="min-h-screen rounded-3xl bg-light-mesh p-10"><div className="mx-auto max-w-4xl space-y-4"><div className="skeleton h-8 w-48" /><div className="skeleton h-56 w-full" /></div></div>;
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-light-mesh text-slate-900 p-10 flex flex-col items-center justify-center rounded-3xl">
        <AlertTriangle size={48} className="text-amber-500 mb-4" />
        <h1 className="text-2xl font-bold">{loadFailed ? 'Không thể tải yêu cầu' : 'Không tìm thấy yêu cầu'}</h1>
        <p className="text-slate-500 text-sm mt-1">{loadFailed ? 'Hệ thống không thể xác minh yêu cầu này. Vui lòng thử lại sau.' : `Mã yêu cầu "${reqId}" không tồn tại hoặc bạn không có quyền truy cập.`}</p>
        <Link
          href="/employee/requests"
          className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-300 bg-white hover:border-blue-300 hover:text-blue-700 text-slate-700 text-sm font-medium transition shadow-sm"
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
  const completedItems = request.items.filter((item) => item.status === 'COMPLETED').length;

  return (
    <div className="min-h-screen bg-light-mesh text-slate-900 selection:bg-blue-100 selection:text-blue-900 p-6 lg:p-10 relative overflow-hidden font-sans rounded-2xl">

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-blue-700 transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-slate-300" />
          <Link href="/employee/requests" className="hover:text-blue-700 transition-colors">
            My Service Requests
          </Link>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-blue-700 font-mono font-medium">{request.id}</span>
        </div>

        {/* Back Link */}
        <div className="mt-4">
          <Link
            href="/employee/requests"
            className="inline-flex items-center gap-2 text-xs text-slate-600 hover:text-blue-700 transition-colors"
          >
            <ArrowLeft size={16} />
            <span>Quay lại danh sách</span>
          </Link>
        </div>
      </header>

      {/* REJECTED BANNER (If status === REJECTED) */}
      {isRejected && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50/85 px-5 py-4 flex items-start gap-3.5 relative z-10 backdrop-blur-md shadow-sm">
          <XCircle size={20} className="text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-red-800 font-semibold">Yêu cầu đã bị từ chối</p>
            <p className="text-xs text-red-700 mt-1 leading-relaxed">
              Lý do: {request.rejectionReason || 'Không đủ điều kiện phê duyệt.'}
            </p>
            <div className="mt-3">
              <Link
                href="/employee/catalog"
                className="rounded-lg border border-red-200 bg-white hover:bg-red-100 px-4 py-2 text-xs text-red-700 font-medium transition inline-flex items-center gap-1.5"
              >
                <span>Gửi yêu cầu mới</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* TOP CARD */}
      <div className="glass-card-light rounded-3xl p-6 sm:p-8 relative z-10">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[11px] tracking-[0.1em] text-blue-700 font-medium">
              {request.id}
            </div>
            <h1 className="mt-2 text-2xl xl:text-3xl font-semibold text-slate-900 tracking-tight">
              {request.title}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-slate-600 max-w-2xl">
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

          </div>
        </div>

        {/* Meta Grid (4 Tiles) */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 border-t border-slate-200">
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <CalendarDays size={16} className="text-blue-600" />
              <span>Ngày tạo</span>
            </div>
            <div className="text-sm text-slate-800 font-medium truncate">{request.createdAt}</div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <UserRound size={16} className="text-blue-600" />
              <span>Người yêu cầu</span>
            </div>
            <div className="text-sm text-slate-800 font-medium truncate">{request.requester}</div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Users size={16} className="text-blue-600" />
              <span>Phòng ban</span>
            </div>
            <div className="text-sm text-slate-800 font-medium truncate">{request.department}</div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Building2 size={16} className="text-blue-600" />
              <span>Cost Center</span>
            </div>
            <div className="text-sm text-slate-800 font-mono font-medium truncate">{request.costCenter}</div>
          </div>
        </div>
      </div>

      {/* BODY GRID: Timeline & Items */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.95fr)] relative z-10">
        {/* LEFT COLUMN — REQUEST TIMELINE */}
        <section className="glass-card-light rounded-3xl p-6 sm:p-8 flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <GitPullRequest size={18} className="text-blue-600" />
              <span>Timeline Xử Lý</span>
            </h2>

            {/* Vertical timeline */}
            <div className="mt-6 relative pl-2">
              {/* Vertical connecting line */}
              <div className="absolute left-[19px] top-3 bottom-3 w-px bg-slate-200 pointer-events-none" />

              <div className="space-y-6">
                {request.timeline.map((step, idx) => {
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
                          <div className="size-10 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold shadow-md">
                            <Check size={18} strokeWidth={3} />
                          </div>
                        ) : isCurrent ? (
                          <div className="relative size-10 rounded-full border-2 border-blue-500 bg-blue-50 text-blue-700 flex items-center justify-center font-bold shadow-md shadow-blue-500/15">
                            <span className="absolute inset-0 rounded-full ring-2 ring-blue-400/35 animate-ping" />
                            <span className="text-xs font-mono">{idx + 1}</span>
                          </div>
                        ) : (
                          <div className="size-10 rounded-full border border-slate-200 bg-slate-50 text-slate-400 flex items-center justify-center font-mono text-xs">
                            {idx + 1}
                          </div>
                        )}
                      </div>

                      {/* Step Content */}
                      <div className="pt-1.5 flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3
                            className={`text-sm font-medium ${
                              isCurrent ? 'text-blue-700 font-semibold' : isDone ? 'text-slate-900' : 'text-slate-500'
                            }`}
                          >
                            {step.title} <span className="text-xs text-slate-400 font-normal">({step.subTitle})</span>
                          </h3>
                          {step.doneAt && (
                            <span className="font-mono text-[10px] text-slate-400 shrink-0">{step.doneAt}</span>
                          )}
                        </div>

                        {/* Step Note */}
                        {step.note && (
                          <p
                            className={`text-xs mt-1 leading-relaxed ${
                              isCurrent ? 'text-blue-700 font-medium' : 'text-slate-500'
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
        <section className="glass-card-light rounded-3xl p-6 sm:p-8 h-fit lg:sticky lg:top-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <PackageOpen size={18} className="text-blue-600" />
              <span>Fulfillment Items</span>
            </h2>
            <span className="font-mono text-[10px] text-slate-500 border border-slate-200 bg-slate-50 rounded-full px-2.5 py-0.5">
              {request.items.length} ITEMS
            </span>
          </div>

          <p className="text-xs text-slate-500 mt-1.5">
            Mỗi request có thể chứa nhiều hạng mục cấp phát, theo dõi riêng từng item.
          </p>

          <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-blue-900">Tiến độ cấp phát</p>
                <p className="mt-1 text-xs leading-relaxed text-blue-700">{completedItems}/{request.items.length} hạng mục đã hoàn tất</p>
              </div>
              <div className="flex size-12 shrink-0 items-center justify-center rounded-full border-4 border-white bg-blue-600 text-xs font-semibold text-white shadow-sm">
                {Math.round((completedItems / request.items.length) * 100)}%
              </div>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-blue-100">
              <div className="h-full rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${(completedItems / request.items.length) * 100}%` }} />
            </div>
          </div>

          {/* Item Cards List */}
          <div className="mt-5 space-y-3">
            {request.items.map((item) => {
              const itemStatusMeta = STATUS_META[item.status];
              const ItemStatusIcon = itemStatusMeta.icon;

              return (
                <div
                  key={item.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 hover:border-blue-200 hover:bg-blue-50/50 transition-all"
                >
                  {/* Row 1: ID & Status */}
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-blue-700">{item.id}</span>
                    <span
                      className={`flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full border ${itemStatusMeta.borderClass} ${itemStatusMeta.bgClass} ${itemStatusMeta.textClass} font-medium`}
                    >
                      <ItemStatusIcon size={12} />
                      <span>{itemStatusMeta.label}</span>
                    </span>
                  </div>

                  {/* Row 2: Item Name & Assignee */}
                  <h3 className="text-sm font-medium text-slate-900 mt-2">{item.name}</h3>
                  {item.assignee && (
                    <div className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
                      <UserRound size={12} className="text-slate-400" />
                      <span>Giao cho: {item.assignee}</span>
                    </div>
                  )}

                  {/* Row 3: Sub-task Chips */}
                  {item.subTasks && item.subTasks.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200 flex flex-wrap gap-1.5">
                      {item.subTasks.map((st) => (
                        <div
                          key={st.id}
                          className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[10px] text-slate-600 inline-flex items-center gap-1.5"
                        >
                          {st.completed ? (
                            <CheckCircle2 size={12} className="text-emerald-600" />
                          ) : (
                            <Circle size={12} className="text-slate-300" />
                          )}
                          <span>{st.title}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Row 4: Updated At Footer */}
                  <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                    <span>Cập nhật: {item.updatedAt}</span>
                    <span className="text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1 cursor-pointer">
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

    </div>
  );
}
