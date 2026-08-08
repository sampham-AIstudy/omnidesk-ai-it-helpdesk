'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  LifeBuoy,
  ArrowRight,
  Search,
  SearchX,
  Laptop,
  KeyRound,
  Package,
  UserPlus,
  Globe,
  Rocket,
} from 'lucide-react';

interface CatalogCategory {
  id: string;
  name: string;
  tag: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  items: string[];
}

const CATEGORIES: CatalogCategory[] = [
  {
    id: 'hardware',
    name: 'Hardware',
    tag: 'HARDWARE',
    icon: Laptop,
    items: ['Xin laptop mới', 'Xin máy in', 'Xin môi trường Dev'],
  },
  {
    id: 'access',
    name: 'Access',
    tag: 'ACCESS',
    icon: KeyRound,
    items: ['Xin quyền VPN', 'Xin quyền Git repo', 'Xin DB access'],
  },
  {
    id: 'software',
    name: 'Software',
    tag: 'SOFTWARE',
    icon: Package,
    items: ['Xin Microsoft 365 license', 'Xin phần mềm kế toán', 'Xin antivirus'],
  },
  {
    id: 'accounts',
    name: 'Accounts',
    tag: 'ACCOUNTS',
    icon: UserPlus,
    items: ['Tạo account nhân viên', 'Xin email alias', 'Reset mật khẩu'],
  },
  {
    id: 'network',
    name: 'Network',
    tag: 'NETWORK',
    icon: Globe,
    items: ['Xin IP tĩnh', 'Xin truy cập mạng nội bộ', 'Xin port forward'],
  },
  {
    id: 'onboarding',
    name: 'Onboarding',
    tag: 'ONBOARDING',
    icon: Rocket,
    items: ['Xin setup máy cho nhân viên mới', 'Xin chuyển máy / bàn làm việc', 'Xin tài nguyên cho dự án mới'],
  },
];

const FILTER_OPTIONS = [
  { value: 'all', label: 'Tất cả danh mục' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'access', label: 'Access' },
  { value: 'software', label: 'Software' },
  { value: 'accounts', label: 'Accounts' },
  { value: 'network', label: 'Network' },
  { value: 'onboarding', label: 'Onboarding' },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.2 } },
};

export default function ITServiceCatalogPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');

  useEffect(() => {
    document.title = 'IT Service Catalog — Request Something';
  }, []);

  const filteredCategories = useMemo(() => {
    return CATEGORIES.filter((cat) => {
      const matchesFilter = selectedFilter === 'all' || cat.id === selectedFilter;
      const query = searchQuery.trim().toLowerCase();
      if (!query) return matchesFilter;

      const nameMatch = cat.name.toLowerCase().includes(query);
      const tagMatch = cat.tag.toLowerCase().includes(query);
      const itemMatch = cat.items.some((item) => item.toLowerCase().includes(query));

      return matchesFilter && (nameMatch || tagMatch || itemMatch);
    });
  }, [searchQuery, selectedFilter]);

  const handleCardClick = (catId: string, subItem?: string) => {
    if (subItem) {
      router.push(`/employee/new-ticket?category=${catId}&item=${encodeURIComponent(subItem)}`);
    } else {
      router.push(`/employee/new-ticket?category=${catId}`);
    }
  };

  const handleResetSearch = () => {
    setSearchQuery('');
    setSelectedFilter('all');
  };

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Subtle background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* PAGE HEADER */}
      <header className="pt-2 pb-8 relative z-10">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-white transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Service Catalog</span>
        </div>

        {/* Header Title Row */}
        <div className="mt-4 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight">
              IT Service Catalog{' '}
              <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Request Something
              </span>
            </h1>
            <p className="mt-3 text-white/55 text-sm leading-relaxed max-w-xl">
              Chọn một dịch vụ có sẵn để tạo Service Request — quy trình chuẩn hóa theo ITIL, được định tuyến tự động tới bộ phận fulfillment phù hợp.
            </p>
          </div>

          <div className="hidden lg:block shrink-0">
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 backdrop-blur">
              <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>REQUEST FLOW · ITIL-READY</span>
            </div>
          </div>
        </div>
      </header>

      {/* INCIDENT vs SERVICE REQUEST BANNER */}
      <div className="mb-8 rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.06] px-5 py-4 flex items-start gap-3.5 relative z-10 backdrop-blur-md">
        <div className="size-9 rounded-lg bg-cyan-400/10 text-cyan-300 flex items-center justify-center shrink-0 mt-0.5">
          <LifeBuoy size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-white/80 font-medium">Bạn cần Dịch vụ hay Báo sự cố?</p>
          <p className="text-xs text-white/50 mt-0.5 leading-relaxed">
            Cần thiết bị / quyền truy cập / phần mềm mới? Chọn dịch vụ trong Catalog. Gặp sự cố đang xảy ra (mất điện, không login được)? Hãy tạo Incident Ticket ngay.
          </p>
          <Link
            href="/employee/new-ticket"
            className="text-xs text-cyan-300 hover:text-cyan-200 underline underline-offset-4 mt-1.5 inline-flex items-center gap-1 font-medium transition-colors"
          >
            <span>Tạo Incident Ticket</span>
            <ArrowRight size={12} />
          </Link>
        </div>
      </div>

      {/* SEARCH + FILTER BAR */}
      <div className="mb-8 flex flex-col md:flex-row gap-3 relative z-10">
        {/* Search input */}
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm dịch vụ (VPN, Laptop, Adobe...)"
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3 pl-12 pr-4 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition font-sans"
          />
        </div>

        {/* Filter select */}
        <select
          value={selectedFilter}
          onChange={(e) => setSelectedFilter(e.target.value)}
          className="rounded-xl border border-white/10 bg-[#0c101c] px-4 py-3 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none cursor-pointer"
        >
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#05070d] text-white">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* SERVICE CATALOG GRID */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {filteredCategories.length > 0 ? (
            <motion.div
              key="grid"
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5"
            >
              {filteredCategories.map((cat) => {
                const Icon = cat.icon;
                return (
                  <motion.div
                    key={cat.id}
                    variants={cardVariants}
                    layout
                    onClick={() => handleCardClick(cat.id)}
                    className="group rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 hover:border-cyan-400/40 hover:bg-white/[0.05] hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
                  >
                    <div>
                      {/* Top Header Row */}
                      <div className="flex items-center justify-between">
                        <div className="size-12 rounded-2xl bg-cyan-400/10 text-cyan-300 flex items-center justify-center">
                          <Icon size={24} strokeWidth={1.75} />
                        </div>
                        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-cyan-400/80 bg-cyan-400/10 border border-cyan-400/20 px-2.5 py-0.5 rounded font-medium">
                          {cat.tag}
                        </span>
                      </div>

                      {/* Category Name */}
                      <h3 className="mt-4 text-lg font-semibold text-white">{cat.name}</h3>

                      {/* Sub-items list */}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {cat.items.map((subItem) => (
                          <button
                            key={subItem}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCardClick(cat.id, subItem);
                            }}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-white/60 group-hover:border-cyan-400/30 group-hover:bg-white/[0.06] inline-flex items-center gap-1.5 transition-all text-left"
                          >
                            <span>{subItem}</span>
                            <ArrowRight size={12} className="text-white/25 group-hover:text-cyan-300 transition-colors" />
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Card Footer */}
                    <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-white/45 font-medium">
                      <span>Xem dịch vụ</span>
                      <ArrowRight size={14} className="text-cyan-300/70 group-hover:translate-x-1 transition-transform" />
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
              <SearchX size={40} className="text-white/20 mx-auto" />
              <p className="mt-4 text-white/70 font-medium text-base">Không tìm thấy dịch vụ phù hợp</p>
              <p className="mt-1 text-sm text-white/45">Thử từ khóa khác hoặc liên hệ IT Help Desk.</p>
              <button
                type="button"
                onClick={handleResetSearch}
                className="mt-5 rounded-xl border border-white/10 bg-white/[0.05] px-5 py-2.5 text-sm text-white/70 hover:text-white hover:border-white/25 transition cursor-pointer"
              >
                Đặt lại tìm kiếm
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
