'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ChevronRight,
  ArrowLeft,
  Globe,
  Mail,
  FolderOpen,
  Cloud,
  AppWindow,
  Database,
  UserRound,
  Gauge,
  Clock,
  MessageSquare,
  AlertTriangle,
  ArrowRight,
  Share2,
  CheckCircle2,
  Loader2,
  OctagonAlert,
  Users,
  Building2,
  CircleDollarSign,
  LifeBuoy,
  GitBranch,
  Bug,
  Plus,
  Network,
  X,
  Server,
  Info,
} from 'lucide-react';
import {
  MOCK_SERVICES,
  HEALTH_STATUS_META,
  ServiceItem,
  ServiceDep,
} from '@/lib/servicesData';

export default function ServiceHealthDetailPage() {
  const params = useParams();
  const router = useRouter();
  const svcId = params?.id as string;

  const [service, setService] = useState<ServiceItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDepNode, setSelectedDepNode] = useState<ServiceDep | null>(null);
  const [showCMDBModal, setShowCMDBModal] = useState(false);
  const [showCreateIncModal, setShowCreateIncModal] = useState(false);
  const [incTitleInput, setIncTitleInput] = useState('');
  const [incPriorityInput, setIncPriorityInput] = useState('P1');

  const incidentsSectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    const found = MOCK_SERVICES.find((s) => s.id === svcId);
    if (found) {
      setService({ ...found });
      document.title = `Sức Khỏe Dịch Vụ — ${found.name}`;
    } else {
      setService(null);
    }
    setLoading(false);
  }, [svcId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!service) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex flex-col items-center justify-center rounded-3xl">
        <AlertTriangle size={48} className="text-amber-400 mb-4" />
        <h1 className="text-2xl font-bold">Không tìm thấy dịch vụ</h1>
        <p className="text-white/50 text-sm mt-1">Dịch vụ với mã "{svcId}" không tồn tại.</p>
        <Link
          href="/manager/services"
          className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition"
        >
          <ArrowLeft size={16} />
          <span>Quay lại Portfolio</span>
        </Link>
      </div>
    );
  }

  const statusMeta = HEALTH_STATUS_META[service.status];

  const handleOpenDepNode = (dep: ServiceDep) => {
    setSelectedDepNode(dep);
    setShowCMDBModal(true);
  };

  const handleCreateIncident = () => {
    if (!incTitleInput.trim()) {
      toast.error('Vui lòng nhập tiêu đề incident.');
      return;
    }

    setService((prev) => (prev ? { ...prev, openIncidents: prev.openIncidents + 1 } : null));
    setShowCreateIncModal(false);
    setIncTitleInput('');
    toast.success(`Đã khởi tạo incident mới tự động gán vào ${service.name}!`);
  };

  const scrollToIncidents = () => {
    incidentsSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/manager/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <Link href="/manager/services" className="hover:text-white transition-colors">
            Service Portfolio
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-cyan-300">{service.name}</span>
        </div>

        {/* Back Link */}
        <div className="mt-4">
          <Link
            href="/manager/services"
            className="inline-flex items-center gap-2 text-xs text-white/60 hover:text-white transition-colors font-medium"
          >
            <ArrowLeft size={16} />
            <span>Quay lại Portfolio</span>
          </Link>
        </div>
      </header>

      {/* TOP BANNER */}
      <div
        className="rounded-3xl border-2 p-6 sm:p-8 relative z-10 backdrop-blur-xl transition-all"
        style={{
          borderColor: `${statusMeta.color}40`,
          backgroundColor: `${statusMeta.color}0A`,
        }}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="size-16 rounded-3xl bg-white/[0.06] text-cyan-300 flex items-center justify-center border border-white/10 shrink-0">
              <Globe size={32} strokeWidth={1.25} />
            </div>

            <div>
              <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40 block">
                {service.type} SERVICE
              </span>
              <h1 className="mt-1 text-3xl font-semibold text-white tracking-tight">{service.name}</h1>
              <p className="mt-1.5 text-sm text-white/55 max-w-2xl leading-relaxed">
                {service.description}
              </p>
            </div>
          </div>

          {/* Right Status & SLA Banner */}
          <div className="flex items-center gap-4 shrink-0">
            <div
              className={`rounded-2xl border px-5 py-3 flex items-center gap-3 ${statusMeta.borderClass} ${statusMeta.bgClass}`}
            >
              <span className={`size-2.5 rounded-full ${statusMeta.dotClass}`} />
              <div className="flex flex-col">
                <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40">STATUS</span>
                <span className={`text-xl font-bold ${statusMeta.textClass}`}>{statusMeta.label}</span>
              </div>
            </div>

            {/* SLA Ring Mini */}
            <div className="relative size-16 flex items-center justify-center shrink-0">
              <svg className="size-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-white/10"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-emerald-400"
                  strokeDasharray="99.9, 100"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <span className="absolute font-mono text-[10px] font-bold text-white">{service.currentSla}</span>
            </div>
          </div>
        </div>

        {/* Meta Chips Row */}
        <div className="mt-6 pt-5 border-t border-white/10 flex flex-wrap gap-2 text-xs text-white/60">
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 inline-flex items-center gap-1.5">
            <UserRound size={14} className="text-cyan-300" />
            <span>Owner: {service.ownerTeam}</span>
          </span>

          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 inline-flex items-center gap-1.5">
            <Gauge size={14} className="text-cyan-300" />
            <span>SLA target: {service.slaTarget}</span>
          </span>

          {service.lastUpdated && (
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 inline-flex items-center gap-1.5">
              <Clock size={14} className="text-cyan-300" />
              <span>Cập nhật: {service.lastUpdated}</span>
            </span>
          )}

          {service.channel && (
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 inline-flex items-center gap-1.5">
              <MessageSquare size={14} className="text-cyan-300" />
              <span>Kênh: {service.channel}</span>
            </span>
          )}
        </div>
      </div>

      {/* IMPACT STRIP */}
      {service.impactSummary && (
        <div className="mt-6 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10 backdrop-blur-md">
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className="text-amber-300 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-200 font-semibold">
                Impact hiện tại — {service.openIncidents} incidents đang mở
              </p>
              <p className="text-xs text-amber-300/80 mt-0.5 leading-relaxed font-sans">
                {service.impactSummary}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={scrollToIncidents}
            className="rounded-xl bg-amber-400/15 border border-amber-400/40 px-4 py-2 text-xs text-amber-200 hover:bg-amber-400/25 transition flex items-center gap-1.5 shrink-0 cursor-pointer font-medium"
          >
            <span>Xem incidents</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* BODY SECTIONS */}
      <main className="mt-6 space-y-6 relative z-10">
        {/* SECTION 1 — DEPENDENCIES (CMDB LINKED) */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Share2 size={18} className="text-cyan-300" />
              <span>Dependencies (CMDB Linked)</span>
            </h2>
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/35">
              CMDB LINKED · {service.dependencies.length} NODES
            </span>
          </div>

          {/* TREE VIEW STRUCTURE */}
          <div className="relative pt-2">
            {/* Root Node */}
            <div className="rounded-2xl border border-cyan-400/40 bg-cyan-400/10 p-4 flex items-center gap-3 max-w-md">
              <div className="size-10 rounded-xl bg-cyan-400/20 text-cyan-300 flex items-center justify-center border border-cyan-400/30 shrink-0">
                <Globe size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">{service.name}</h3>
                <span className="font-mono text-[10px] text-cyan-300/80 uppercase">Business Service (Root)</span>
              </div>
            </div>

            {/* Connecting Vertical Line */}
            <div className="w-px bg-white/15 ml-5 h-6" />

            {/* Children Nodes List */}
            <div className="space-y-3 pl-8 relative border-l border-white/15 ml-5">
              {service.dependencies.map((dep) => {
                let statusBadge = 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300';
                let DepStatusIcon = CheckCircle2;
                if (dep.status === 'WARN') {
                  statusBadge = 'border-amber-400/30 bg-amber-400/10 text-amber-300';
                  DepStatusIcon = Loader2;
                } else if (dep.status === 'DOWN') {
                  statusBadge = 'border-red-400/30 bg-red-400/10 text-red-300';
                  DepStatusIcon = OctagonAlert;
                }

                return (
                  <div
                    key={dep.id}
                    onClick={() => handleOpenDepNode(dep)}
                    className="group rounded-2xl border border-white/10 bg-white/[0.02] p-4 flex items-center justify-between gap-3 hover:border-cyan-400/40 hover:bg-white/[0.04] transition-all duration-300 cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`size-9 rounded-xl border flex items-center justify-center ${statusBadge} shrink-0`}>
                        <DepStatusIcon size={16} className={dep.status === 'WARN' ? 'animate-spin' : ''} />
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-white group-hover:text-cyan-300 transition-colors">
                          {dep.name}
                        </h4>
                        <div className="mt-0.5 flex items-center gap-2 text-[10px] font-mono text-white/40">
                          <span className="uppercase tracking-wider">{dep.kind}</span>
                          <span>•</span>
                          <span>CI: {dep.id}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className={`font-mono text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-md border ${statusBadge}`}>
                        {dep.status}
                      </span>
                      <ChevronRight size={16} className="text-white/25 group-hover:text-cyan-300 group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-white/40">
            <span>Liên kết CMDB • Tự động cập nhật 15 phút/lần</span>
            <button
              type="button"
              onClick={() => toast.success('Mở sơ đồ CMDB Dependency Map toàn hệ thống')}
              className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-white/70 hover:text-white transition flex items-center gap-1.5 cursor-pointer font-medium"
            >
              <Network size={14} />
              <span>Mở CMDB Map</span>
            </button>
          </div>
        </section>

        {/* SECTION 2 — IMPACT ANALYSIS */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Users size={18} className="text-cyan-300" />
              <span>Impact Analysis</span>
            </h2>
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/35">
              {(service.impactedUsers || 0).toLocaleString()} EMPLOYEES
            </span>
          </div>

          {/* Explanation Flow Chain */}
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4 flex flex-wrap items-center gap-2 text-sm">
            {service.impactChain ? (
              service.impactChain.map((step, idx) => (
                <div key={step} className="flex items-center gap-2">
                  <span
                    className={`rounded-xl border px-3.5 py-1.5 text-xs font-semibold ${
                      idx === 0
                        ? 'border-red-400/30 bg-red-400/10 text-red-300'
                        : idx === 1
                        ? 'border-amber-400/30 bg-amber-400/10 text-amber-300'
                        : 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                    }`}
                  >
                    {step}
                  </span>
                  {idx < service.impactChain!.length - 1 && (
                    <ArrowRight size={14} className="text-white/30 shrink-0" />
                  )}
                </div>
              ))
            ) : (
              <span className="text-xs text-white/50">Không có tác động tiêu cực nào được ghi nhận.</span>
            )}
          </div>

          {/* 3 Impact Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
              <div className="flex items-center gap-2 text-xs text-white/45">
                <Building2 size={16} className="text-cyan-300" />
                <span>Phòng ban ảnh hưởng</span>
              </div>
              <p className="text-2xl font-bold text-white">
                {service.impactedDepartments?.length || 0}
              </p>
              <p className="text-[11px] text-white/40 truncate">
                {service.impactedDepartments?.join(', ') || 'Không có'}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
              <div className="flex items-center gap-2 text-xs text-white/45">
                <Users size={16} className="text-cyan-300" />
                <span>Users ảnh hưởng</span>
              </div>
              <p className="text-2xl font-bold text-amber-300">
                {(service.impactedUsers || 0).toLocaleString()}
              </p>
              <p className="text-[11px] text-white/40">1.940 không vào được VPN • 360 gián đoạn</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
              <div className="flex items-center gap-2 text-xs text-white/45">
                <CircleDollarSign size={16} className="text-cyan-300" />
                <span>Tác động doanh thu</span>
              </div>
              <p className="text-2xl font-bold text-amber-300 font-mono">
                {service.revenueImpactHourly || '$0/giờ'}
              </p>
              <p className="text-[11px] text-white/40">ước tính thiệt hại / giờ outage</p>
            </div>
          </div>

          {/* Impacted Employee Preview List */}
          {service.impactedUserList && service.impactedUserList.length > 0 && (
            <div>
              <span className="font-mono uppercase text-[10px] text-white/40 block mb-2">
                NGƯỜI DÙNG ĐANG BỊ ẢNH HƯỞNG (XEM TRƯỚC)
              </span>

              <div className="max-h-56 overflow-y-auto rounded-2xl border border-white/10 bg-white/[0.02] divide-y divide-white/10">
                {service.impactedUserList.map((usr) => (
                  <div key={usr.id} className="p-3.5 flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-3">
                      <div className="size-8 rounded-full bg-white/[0.06] text-white/60 flex items-center justify-center text-xs font-semibold">
                        {usr.name[0]}
                      </div>
                      <div>
                        <p className="text-white/80 font-medium">{usr.name}</p>
                        <p className="text-[10px] text-white/40">{usr.department}</p>
                      </div>
                    </div>

                    <span className="font-mono text-[10px] text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded">
                      {usr.impactReason}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* SECTION 3 — OPEN INCIDENTS */}
        <section ref={incidentsSectionRef} className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <LifeBuoy size={18} className="text-red-400" />
              <span>Open Incidents</span>
            </h2>
            <span className="font-mono text-[10px] text-red-300 bg-red-400/10 border border-red-400/30 px-2.5 py-1 rounded-full font-semibold">
              {service.openIncidents} INCIDENTS
            </span>
          </div>

          <div className="space-y-2.5">
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex items-center justify-between gap-3 hover:border-white/25 transition cursor-pointer">
              <div className="flex items-center gap-3 min-w-0">
                <span className="font-mono text-[11px] text-red-300 font-bold">INC-10570</span>
                <div>
                  <h4 className="text-xs font-medium text-white/80">VPN Authentication Failed</h4>
                  <p className="text-[10px] text-white/40">Network Team • P1 Critical • Nguyen Van A • 06/08 14:02</p>
                </div>
              </div>
              <ChevronRight size={16} className="text-white/25" />
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex items-center justify-between gap-3 hover:border-white/25 transition cursor-pointer">
              <div className="flex items-center gap-3 min-w-0">
                <span className="font-mono text-[11px] text-amber-300 font-bold">INC-10422</span>
                <div>
                  <h4 className="text-xs font-medium text-white/80">VPN slow on branch HN</h4>
                  <p className="text-[10px] text-white/40">Network Team • P2 High • Trần Thị Bích • 06/08 11:30</p>
                </div>
              </div>
              <ChevronRight size={16} className="text-white/25" />
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex items-center justify-between gap-3 hover:border-white/25 transition cursor-pointer">
              <div className="flex items-center gap-3 min-w-0">
                <span className="font-mono text-[11px] text-zinc-400 font-bold">INC-10398</span>
                <div>
                  <h4 className="text-xs font-medium text-white/80">Cannot reach 10.0.4.x subnet</h4>
                  <p className="text-[10px] text-white/40">Network Team • P3 Medium • Lê Minh Công • 05/08 16:45</p>
                </div>
              </div>
              <ChevronRight size={16} className="text-white/25" />
            </div>
          </div>

          <div className="pt-3 border-t border-white/10 flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => setShowCreateIncModal(true)}
              className="rounded-lg border border-dashed border-white/15 hover:border-cyan-400/40 px-3.5 py-2 text-xs text-white/60 hover:text-white transition inline-flex items-center gap-1.5 cursor-pointer font-medium"
            >
              <Plus size={14} />
              <span>Tạo Incident mới</span>
            </button>

            <Link href="/manager/major-incidents" className="text-cyan-300 hover:underline">
              Xem tất cả incidents của dịch vụ
            </Link>
          </div>
        </section>

        {/* SECTION 4 — ACTIVE CHANGES & PROBLEMS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Changes */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <GitBranch size={18} className="text-blue-400" />
                <span>Active Changes</span>
              </h3>
              <span className="font-mono text-[10px] text-blue-300 bg-blue-400/10 border border-blue-400/30 px-2 py-0.5 rounded-full font-semibold">
                {service.activeChanges} ACTIVE
              </span>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
              <div className="flex justify-between items-start">
                <span className="font-mono text-[11px] text-blue-300 font-bold">CHG-0214</span>
                <span className="font-mono text-[9px] text-blue-300 bg-blue-400/10 border border-blue-400/30 px-2 py-0.5 rounded uppercase">
                  SCHEDULED
                </span>
              </div>
              <p className="text-xs font-semibold text-white">Upgrade VPN Gateway firmware 8.1.2</p>
              <p className="text-[11px] text-white/45">Lịch thực hiện: 09/08 00:00 • Dự kiến downtime: 10 phút</p>
              <div className="pt-2 text-[10px] font-mono text-white/40">Tiến độ: 3/6 tasks hoàn thành</div>
            </div>
          </div>

          {/* Problems */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Bug size={18} className="text-orange-400" />
                <span>Problems</span>
              </h3>
              <span className="font-mono text-[10px] text-orange-300 bg-orange-400/10 border border-orange-400/30 px-2 py-0.5 rounded-full font-semibold">
                {service.problems} PROBLEM
              </span>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
              <div className="flex justify-between items-start">
                <span className="font-mono text-[11px] text-orange-300 font-bold">PRB-0081</span>
                <span className="font-mono text-[9px] text-orange-300 bg-orange-400/10 border border-orange-400/30 px-2 py-0.5 rounded uppercase">
                  INVESTIGATION
                </span>
              </div>
              <p className="text-xs font-semibold text-white">Recurring VPN disconnect after firmware 8.0</p>
              <p className="text-[11px] text-white/45">Đang điều tra nguyên nhân gốc • Chưa có RCA chính thức</p>
            </div>
          </div>
        </div>
      </main>

      {/* MODAL 1: CMDB NODE DETAIL */}
      <AnimatePresence>
        {showCMDBModal && selectedDepNode && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-cyan-400/30 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <div>
                  <span className="font-mono text-[10px] text-cyan-300 font-bold">CMDB ITEM</span>
                  <h3 className="text-base font-semibold text-white">{selectedDepNode.name}</h3>
                </div>
                <button type="button" onClick={() => setShowCMDBModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-white/45">Mã CI Tag</span>
                  <span className="font-mono text-cyan-300">{selectedDepNode.id}</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-white/45">Phân loại Kind</span>
                  <span className="font-mono text-white/80">{selectedDepNode.kind}</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-white/45">Trạng thái Health</span>
                  <span className="font-mono text-emerald-300">{selectedDepNode.status}</span>
                </div>
                <div className="flex justify-between border-b border-white/5 pb-1.5">
                  <span className="text-white/45">Đơn vị quản lý</span>
                  <span className="text-white/80">{selectedDepNode.owner || 'Network Team'}</span>
                </div>
                {selectedDepNode.ip && (
                  <div className="flex justify-between border-b border-white/5 pb-1.5">
                    <span className="text-white/45">Địa chỉ IP</span>
                    <span className="font-mono text-white/80">{selectedDepNode.ip}</span>
                  </div>
                )}
                {selectedDepNode.rack && (
                  <div className="flex justify-between border-b border-white/5 pb-1.5">
                    <span className="text-white/45">Vị trí Rack</span>
                    <span className="font-mono text-white/80">{selectedDepNode.rack}</span>
                  </div>
                )}
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCMDBModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Đóng
                </button>
                <button
                  type="button"
                  onClick={() => {
                    toast.success(`Mở bản ghi ${selectedDepNode.id} trong CMDB Module`);
                    setShowCMDBModal(false);
                  }}
                  className="px-4 py-2 rounded-xl bg-cyan-500 text-xs font-semibold text-black hover:bg-cyan-400 transition"
                >
                  Mở trong CMDB
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 2: CREATE INCIDENT */}
      <AnimatePresence>
        {showCreateIncModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Tạo Incident cho {service.name}</h3>
                <button type="button" onClick={() => setShowCreateIncModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-xs text-white/60">Tiêu đề Incident</label>
                  <input
                    type="text"
                    value={incTitleInput}
                    onChange={(e) => setIncTitleInput(e.target.value)}
                    placeholder="Mô tả tóm tắt sự cố..."
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs text-white/60">Mức độ ưu tiên</label>
                  <select
                    value={incPriorityInput}
                    onChange={(e) => setIncPriorityInput(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-[#05070d] p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  >
                    <option value="P1">P1 - Critical</option>
                    <option value="P2">P2 - High</option>
                    <option value="P3">P3 - Medium</option>
                  </select>
                </div>

                <p className="text-xs text-white/45 bg-white/[0.03] p-3 rounded-xl border border-white/10">
                  Incident sẽ tự động được gán cho <strong>{service.name} ({service.id})</strong> và phòng ban <strong>{service.ownerTeam}</strong>.
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateIncModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleCreateIncident}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-lg cursor-pointer"
                >
                  Tạo Incident
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
