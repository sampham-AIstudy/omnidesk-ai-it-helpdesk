'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
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
  Monitor,
} from 'lucide-react';
import api from '@/lib/api';
import type { ServiceCatalogItem } from '@/lib/serviceCatalog';

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
    items: ['Xin laptop mới', 'Xin máy in', 'Xin thiết bị ngoại vi'],
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
    items: ['Xin Microsoft 365 license', 'Yêu cầu cài đặt phần mềm được phê duyệt', 'Xin antivirus'],
  },
  {
    id: 'accounts',
    name: 'Accounts',
    tag: 'ACCOUNTS',
    icon: UserPlus,
    items: ['Đặt lại mật khẩu', 'Mở khóa tài khoản', 'Xin email alias', 'Cập nhật tên hiển thị / email'],
  },
  {
    id: 'network',
    name: 'Network',
    tag: 'NETWORK',
    icon: Globe,
    items: ['Xin IP tĩnh', 'Xin truy cập mạng nội bộ', 'Đăng ký Wi-Fi cho thiết bị mới'],
  },
  {
    id: 'onboarding',
    name: 'Workplace support',
    tag: 'WORKPLACE',
    icon: Monitor,
    items: ['Đăng ký mượn thiết bị tạm thời', 'Xin chuyển máy / bàn làm việc', 'Yêu cầu hỗ trợ thiết bị phòng họp'],
  },
];

const FILTER_OPTIONS = [
  { value: 'all', label: 'Tất cả danh mục' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'access', label: 'Access' },
  { value: 'software', label: 'Software' },
  { value: 'accounts', label: 'Accounts' },
  { value: 'network', label: 'Network' },
  { value: 'onboarding', label: 'Workplace support' },
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
} as const;

export default function ITServiceCatalogPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');
  const catalogQuery = useQuery({
    queryKey: ['service-catalog'],
    queryFn: async () => (await api.get<{ items: ServiceCatalogItem[] }>('/service-requests/catalog')).data.items,
    staleTime: 60_000,
  });

  useEffect(() => {
    document.title = 'IT Service Catalog — Request Something';
  }, []);

  const catalogCategories = useMemo(() => CATEGORIES.map((category) => ({
    ...category,
    items: (catalogQuery.data ?? [])
      .filter((item) => item.category === category.id)
      .map((item) => item.service_name),
  })), [catalogQuery.data]);

  const filteredCategories = useMemo(() => {
    return catalogCategories.filter((cat) => {
      const matchesFilter = selectedFilter === 'all' || cat.id === selectedFilter;
      const query = searchQuery.trim().toLowerCase();
      if (!query) return matchesFilter;

      const nameMatch = cat.name.toLowerCase().includes(query);
      const tagMatch = cat.tag.toLowerCase().includes(query);
      const itemMatch = cat.items.some((item) => item.toLowerCase().includes(query));

      return matchesFilter && (nameMatch || tagMatch || itemMatch);
    });
  }, [catalogCategories, searchQuery, selectedFilter]);

  const handleCardClick = (catId: string, subItem?: string) => {
    if (subItem) {
      router.push(`/employee/catalog/${catId}?service=${encodeURIComponent(subItem)}`);
    } else {
      router.push(`/employee/catalog/${catId}`);
    }
  };

  const handleResetSearch = () => {
    setSearchQuery('');
    setSelectedFilter('all');
  };

  return (
    <div className="min-h-screen bg-light-mesh text-slate-900 selection:bg-blue-100 selection:text-blue-900 p-6 lg:p-10 relative overflow-hidden font-sans rounded-2xl">

      {/* PAGE HEADER */}
      <header className="pt-2 pb-8 relative z-10">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono tracking-wide">
          <Link href="/employee/dashboard" className="hover:text-blue-700 transition-colors">
            Home
          </Link>
          <ChevronRight size={14} className="text-slate-300" />
          <span className="text-slate-700">Service Catalog</span>
        </div>

        {/* Header Title Row */}
        <div className="mt-4 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-slate-900 tracking-tight">
              IT Service Catalog{' '}
              Request Something
            </h1>
            <p className="mt-3 text-slate-600 text-sm leading-relaxed max-w-xl">
              Chọn một dịch vụ có sẵn để tạo Service Request — quy trình chuẩn hóa theo ITIL, được định tuyến tự động tới bộ phận fulfillment phù hợp.
            </p>
          </div>

          <div className="hidden lg:block shrink-0">
            <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-slate-500 flex items-center gap-2 rounded-xl border border-slate-200 bg-white/75 px-3.5 py-2 backdrop-blur">
              <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>REQUEST FLOW · ITIL-READY</span>
            </div>
          </div>
        </div>
      </header>

      {/* INCIDENT vs SERVICE REQUEST BANNER */}
       <div className="mb-8 rounded-2xl border border-blue-200 bg-blue-50/80 px-5 py-4 flex items-start gap-3.5 relative z-10 backdrop-blur-md shadow-sm">
         <div className="size-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 mt-0.5">
          <LifeBuoy size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-800 font-medium">Bạn cần Dịch vụ hay Báo sự cố?</p>
          <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
            Cần thiết bị / quyền truy cập / phần mềm mới? Chọn dịch vụ trong Catalog. Gặp sự cố đang xảy ra (mất điện, không login được)? Hãy tạo Incident Ticket ngay.
          </p>
          <Link
            href="/employee/new-ticket"
             className="text-xs text-blue-700 hover:text-blue-800 underline underline-offset-4 mt-1.5 inline-flex items-center gap-1 font-medium transition-colors"
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
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm dịch vụ (VPN, Laptop, Adobe...)"
            className="w-full rounded-xl border border-slate-300 bg-white/90 py-3 pl-12 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 transition font-sans shadow-sm"
          />
        </div>

        {/* Filter select */}
        <select
          value={selectedFilter}
          onChange={(e) => setSelectedFilter(e.target.value)}
          className="rounded-xl border border-slate-300 bg-white/90 px-4 py-3 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 cursor-pointer shadow-sm"
        >
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-white text-slate-900">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* SERVICE CATALOG GRID */}
      <div className="relative z-10">
        {catalogQuery.isLoading && <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3" aria-label="Đang tải service catalog">{Array.from({ length: 6 }, (_, index) => <div key={index} className="h-56 rounded-2xl border border-slate-200 bg-white p-6"><div className="skeleton h-12 w-12" /><div className="mt-5 skeleton h-5 w-28" /><div className="mt-3 skeleton h-12 w-full" /></div>)}</div>}
        {catalogQuery.isError && <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">Không thể tải Service Catalog từ hệ thống. Vui lòng thử lại sau.</div>}
        {!catalogQuery.isLoading && !catalogQuery.isError && (
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
                    className="group glass-card-light glass-card-light-hover rounded-3xl p-6 hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
                  >
                    <div>
                      {/* Top Header Row */}
                      <div className="flex items-center justify-between">
                        <div className="size-12 rounded-2xl bg-blue-100 text-blue-700 flex items-center justify-center">
                          <Icon size={24} strokeWidth={1.75} />
                        </div>
                        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded font-medium">
                          {cat.tag}
                        </span>
                      </div>

                      {/* Category Name */}
                      <h3 className="mt-4 text-lg font-semibold text-slate-900">{cat.name}</h3>

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
                            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 group-hover:border-blue-200 group-hover:bg-blue-50 inline-flex items-center gap-1.5 transition-all text-left"
                          >
                            <span>{subItem}</span>
                            <ArrowRight size={12} className="text-slate-400 group-hover:text-blue-700 transition-colors" />
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Card Footer */}
                    <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 font-medium">
                      <span>Xem dịch vụ</span>
                      <ArrowRight size={14} className="text-blue-600 group-hover:translate-x-1 transition-transform" />
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
              <SearchX size={40} className="text-slate-300 mx-auto" />
              <p className="mt-4 text-slate-800 font-medium text-base">Không tìm thấy dịch vụ phù hợp</p>
              <p className="mt-1 text-sm text-slate-500">Thử từ khóa khác hoặc liên hệ IT Help Desk.</p>
              <button
                type="button"
                onClick={handleResetSearch}
                className="mt-5 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm text-slate-700 hover:text-blue-700 hover:border-blue-300 transition cursor-pointer"
              >
                Đặt lại tìm kiếm
              </button>
            </motion.div>
          )}
        </AnimatePresence>
        )}
      </div>
    </div>
  );
}
