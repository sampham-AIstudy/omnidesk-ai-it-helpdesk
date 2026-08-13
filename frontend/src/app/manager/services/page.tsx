'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  Search,
  Users,
  UserRound,
  Gauge,
  Globe,
  Mail,
  FolderOpen,
  Cloud,
  AppWindow,
  Database,
  CheckCircle2,
  Loader2,
  OctagonAlert,
  SearchX,
  RefreshCw,
  Activity,
  Layers,
} from 'lucide-react';
import {
  MOCK_SERVICES,
  HEALTH_STATUS_META,
  ServiceItem,
  HealthStatus,
  ServiceType,
} from '@/lib/servicesData';

const TYPE_OPTIONS = [
  { value: 'all', label: 'Tất cả loại' },
  { value: 'BUSINESS', label: 'Business Service' },
  { value: 'TECHNICAL', label: 'Technical Service' },
];

export default function ServicePortfolioListPage() {
  const router = useRouter();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatuses, setSelectedStatuses] = useState<HealthStatus[]>([
    'OPERATIONAL',
    'DEGRADED',
    'PARTIAL_OUTAGE',
    'MAJOR_OUTAGE',
    'MAINTENANCE',
  ]);

  useEffect(() => {
    document.title = 'Service Portfolio — IT Service Health';
  }, []);

  const toggleStatus = (st: HealthStatus) => {
    setSelectedStatuses((prev) =>
      prev.includes(st) ? prev.filter((s) => s !== st) : [...prev, st]
    );
  };

  const filteredServices = useMemo(() => {
    return MOCK_SERVICES.filter((svc) => {
      const matchesType = selectedType === 'all' || svc.type === selectedType;
      const matchesStatus = selectedStatuses.includes(svc.status);
      const q = searchQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        svc.name.toLowerCase().includes(q) ||
        svc.ownerTeam.toLowerCase().includes(q) ||
        svc.id.toLowerCase().includes(q);

      return matchesType && matchesStatus && matchesQuery;
    });
  }, [searchQuery, selectedType, selectedStatuses]);

  const handleCardClick = (id: string) => {
    router.push(`/manager/services/${id}`);
  };

  const renderServiceIcon = (iconName: string) => {
    const props = { size: 24, strokeWidth: 1.5 };
    switch (iconName) {
      case 'Globe':
        return <Globe {...props} />;
      case 'Mail':
        return <Mail {...props} />;
      case 'FolderOpen':
        return <FolderOpen {...props} />;
      case 'Cloud':
        return <Cloud {...props} />;
      case 'AppWindow':
        return <AppWindow {...props} />;
      case 'Database':
        return <Database {...props} />;
      default:
        return <Globe {...props} />;
    }
  };

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/manager/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Service Portfolio</span>
        </div>

        {/* Title Row */}
        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              Service Portfolio{' '}
              <span className="from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Sức Khỏe Dịch Vụ
              </span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Theo dõi các Business & Technical Service được xây dựng trên nền CMDB — gắn kết incidents, changes, problems để phân tích ownership, dependencies và business impact.
            </p>
          </div>

          {/* Right Health Summary Cards */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-center min-w-20">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-emerald-400 block font-semibold">OPERATIONAL</span>
              <span className="text-xl font-bold text-emerald-300">8</span>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-center min-w-20">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-amber-400 block font-semibold">DEGRADED</span>
              <span className="text-xl font-bold text-amber-300">2</span>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-center min-w-20">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-red-400 block font-semibold">OUTAGE</span>
              <span className="text-xl font-bold text-red-300">1</span>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-center min-w-20">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-blue-400 block font-semibold">MAINT</span>
              <span className="text-xl font-bold text-blue-300">1</span>
            </div>
          </div>
        </div>
      </header>

      {/* OVERALL HEALTH RING CARD */}
      <div className="mb-6 rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 flex items-center gap-6 flex-wrap relative z-10">
        <div className="relative size-24 shrink-0 flex items-center justify-center">
          <svg className="size-full transform -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-white/10"
              strokeWidth="3"
              stroke="currentColor"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className="text-cyan-400"
              strokeDasharray="85, 100"
              strokeWidth="3"
              strokeLinecap="round"
              stroke="currentColor"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className="text-2xl font-bold text-white leading-none">85%</span>
            <span className="font-mono text-[8px] text-white/40 mt-0.5 tracking-wider uppercase">AVAILABILITY</span>
          </div>
        </div>

        <div className="flex-1 min-w-64">
          <h2 className="text-base font-semibold text-white">Sức khỏe tổng thể hệ thống dịch vụ</h2>
          <p className="text-xs text-white/50 mt-1 leading-relaxed">
            12/12 dịch vụ được theo dõi liên tục qua CMDB • 2 dịch vụ đang suy giảm • 1 dịch vụ mất khả năng hoạt động.
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {(Object.keys(HEALTH_STATUS_META) as HealthStatus[]).map((st) => {
              const meta = HEALTH_STATUS_META[st];
              return (
                <span
                  key={st}
                  className={`font-mono text-[9px] uppercase tracking-[0.15em] rounded-full border px-2.5 py-0.5 flex items-center gap-1.5 ${meta.borderClass} ${meta.bgClass} ${meta.textClass}`}
                >
                  <span className={`size-1.5 rounded-full ${meta.dotClass}`} />
                  <span>{meta.label}</span>
                </span>
              );
            })}
          </div>
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
            placeholder="Tìm dịch vụ, chủ sở hữu..."
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3 pl-12 pr-4 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition font-sans"
          />
        </div>

        {/* Type select */}
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded-xl border border-white/10 bg-[#0c101c] px-4 py-3 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none cursor-pointer"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#05070d] text-white">
              {opt.label}
            </option>
          ))}
        </select>

        {/* Status multi-toggle chips */}
        <div className="flex gap-1.5 flex-wrap items-center">
          {(Object.keys(HEALTH_STATUS_META) as HealthStatus[]).map((st) => {
            const isSelected = selectedStatuses.includes(st);
            const meta = HEALTH_STATUS_META[st];
            return (
              <button
                key={st}
                type="button"
                onClick={() => toggleStatus(st)}
                className={`font-mono text-xs px-3 py-2.5 rounded-xl border transition cursor-pointer font-semibold ${
                  isSelected
                    ? `${meta.borderClass} ${meta.bgClass} ${meta.textClass}`
                    : 'border-white/10 bg-white/[0.02] text-white/40 hover:text-white'
                }`}
              >
                {st}
              </button>
            );
          })}
        </div>
      </div>

      {/* SERVICE CARDS GRID */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {filteredServices.length > 0 ? (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5"
            >
              {filteredServices.map((svc) => {
                const statusMeta = HEALTH_STATUS_META[svc.status];
                const targetSlaNum = parseFloat(svc.slaTarget.replace('%', ''));
                const currentSlaNum = parseFloat(svc.currentSla.replace('%', ''));
                const meetsSla = currentSlaNum >= targetSlaNum;

                return (
                  <motion.div
                    key={svc.id}
                    layout
                    whileHover={{ y: -4 }}
                    onClick={() => handleCardClick(svc.id)}
                    className="group rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 hover:border-cyan-400/40 hover:bg-white/[0.05] transition-all duration-300 cursor-pointer flex flex-col justify-between"
                  >
                    <div>
                      {/* Row 1: Icon Chip & Health Status */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="size-12 rounded-2xl bg-white/[0.05] text-cyan-300 flex items-center justify-center border border-white/10 group-hover:border-cyan-400/40 transition-colors">
                          {renderServiceIcon(svc.iconName)}
                        </div>

                        <span
                          className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-full border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium`}
                        >
                          <span className={`size-1.5 rounded-full ${statusMeta.dotClass}`} />
                          <span>{statusMeta.label}</span>
                        </span>
                      </div>

                      {/* Title & Type */}
                      <h3 className="mt-4 text-lg font-semibold text-white group-hover:text-cyan-300 transition-colors">
                        {svc.name}
                      </h3>
                      <span className="mt-1 inline-flex font-mono text-[9px] uppercase tracking-[0.2em] text-white/35 rounded px-1.5 py-0.5 border border-white/10">
                        {svc.type} SERVICE
                      </span>

                      {/* Owner & SLA Row */}
                      <div className="mt-4 flex items-center gap-2 text-xs text-white/50 flex-wrap font-sans">
                        <span className="flex items-center gap-1">
                          <UserRound size={12} className="text-white/40" />
                          <span>{svc.ownerTeam}</span>
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Gauge size={12} className="text-white/40" />
                          <span>SLA {svc.slaTarget}</span>
                        </span>
                        <span>•</span>
                        <span
                          className={`font-mono text-[10px] font-semibold px-2 py-0.5 rounded ${
                            meetsSla
                              ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/30'
                              : 'bg-amber-400/10 text-amber-300 border border-amber-400/30'
                          }`}
                        >
                          {svc.currentSla}
                        </span>
                      </div>

                      {/* Dependencies Preview */}
                      <div className="mt-4">
                        <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/35 block mb-2">
                          DEPENDENCIES ({svc.dependencies.length})
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {svc.dependencies.slice(0, 4).map((dep) => {
                            let depStyle = 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300';
                            let DepIcon = CheckCircle2;
                            if (dep.status === 'WARN') {
                              depStyle = 'border-amber-400/30 bg-amber-400/10 text-amber-300';
                              DepIcon = Loader2;
                            } else if (dep.status === 'DOWN') {
                              depStyle = 'border-red-400/30 bg-red-400/10 text-red-300';
                              DepIcon = OctagonAlert;
                            }

                            return (
                              <div
                                key={dep.id}
                                title={dep.name}
                                className={`size-7 rounded-lg border flex items-center justify-center ${depStyle}`}
                              >
                                <DepIcon size={12} className={dep.status === 'WARN' ? 'animate-spin' : ''} />
                              </div>
                            );
                          })}
                          {svc.dependencies.length > 4 && (
                            <div className="size-7 rounded-lg border border-white/10 bg-white/[0.04] text-[10px] font-mono text-white/40 flex items-center justify-center">
                              +{svc.dependencies.length - 4}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Impact Strip */}
                      {svc.impactedUsers && (
                        <div className="mt-4 rounded-xl border border-amber-400/25 bg-amber-400/[0.05] px-3 py-2 text-[11px] text-amber-300 flex items-center gap-2 font-medium">
                          <Users size={14} className="shrink-0 text-amber-400" />
                          <span className="truncate">{svc.impactedUsers.toLocaleString()} employees impacted</span>
                        </div>
                      )}
                    </div>

                    {/* Footer Stats Grid */}
                    <div className="mt-5 pt-4 border-t border-white/10 grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-lg py-2 hover:bg-white/[0.04] transition">
                        <span className={`text-base font-semibold block leading-none ${svc.openIncidents > 0 ? 'text-red-400' : 'text-white'}`}>
                          {svc.openIncidents}
                        </span>
                        <span className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/40 mt-1 block">
                          OPEN INC
                        </span>
                      </div>

                      <div className="rounded-lg py-2 hover:bg-white/[0.04] transition">
                        <span className="text-base font-semibold text-blue-400 block leading-none">
                          {svc.activeChanges}
                        </span>
                        <span className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/40 mt-1 block">
                          ACTIVE CHG
                        </span>
                      </div>

                      <div className="rounded-lg py-2 hover:bg-white/[0.04] transition">
                        <span className="text-base font-semibold text-orange-400 block leading-none">
                          {svc.problems}
                        </span>
                        <span className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/40 mt-1 block">
                          PROBLEMS
                        </span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          ) : (
            /* EMPTY STATE */
            <div className="py-20 text-center flex flex-col items-center justify-center rounded-3xl border border-white/10 bg-white/[0.02]">
              <SearchX size={40} className="text-white/20 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Không tìm thấy dịch vụ</p>
              <p className="mt-1 text-sm text-white/45">Thử từ khóa hoặc bộ lọc khác.</p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSelectedType('all');
                  setSelectedStatuses(['OPERATIONAL', 'DEGRADED', 'PARTIAL_OUTAGE', 'MAJOR_OUTAGE', 'MAINTENANCE']);
                }}
                className="mt-5 rounded-xl border border-white/10 bg-white/[0.05] px-5 py-2.5 text-sm text-white/70 hover:text-white transition cursor-pointer inline-flex items-center gap-2"
              >
                <RefreshCw size={14} />
                <span>Đặt lại bộ lọc</span>
              </button>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
