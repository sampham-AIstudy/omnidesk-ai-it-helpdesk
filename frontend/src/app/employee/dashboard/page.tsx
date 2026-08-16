'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { 
  CheckCircle2, Clock3, Inbox, ShieldCheck,
  Search, Laptop, Wifi, KeyRound, AlertOctagon, ExternalLink, ArrowRight 
} from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import { EmptyState, Spinner } from '@/components/ui';
import { useAuthStore } from '@/lib/authStore';
import { Ticket } from '@/types';
import api from '@/lib/api';

const SERVICE_CATALOG = [
  {
    id: 'hardware',
    title: 'Cấp phát thiết bị',
    desc: 'Yêu cầu laptop mới, màn hình rời, chuột/bàn phím hoặc phụ kiện IT',
    icon: Laptop,
    badge: 'Phần cứng',
    color: 'from-blue-500 to-indigo-600',
    bgColor: 'bg-blue-50/80',
    borderColor: 'border-blue-200/80',
    textColor: 'text-blue-700',
    href: '/employee/catalog/hardware',
  },
  {
    id: 'access',
    title: 'VPN & quyền truy cập',
    desc: 'Đăng ký VPN làm việc từ xa, quyền Git repository hoặc quyền truy cập hệ thống',
    icon: Wifi,
    badge: 'Quyền truy cập',
    color: 'from-cyan-500 to-blue-600',
    bgColor: 'bg-cyan-50/80',
    borderColor: 'border-cyan-200/80',
    textColor: 'text-cyan-700',
    href: '/employee/catalog/access',
  },
  {
    id: 'network',
    title: 'Kết nối mạng văn phòng',
    desc: 'Đăng ký Wi-Fi cho thiết bị mới, IP tĩnh hoặc quyền mạng nội bộ',
    icon: Wifi,
    badge: 'Hạ tầng mạng',
    color: 'from-sky-500 to-cyan-600',
    bgColor: 'bg-sky-50/80',
    borderColor: 'border-sky-200/80',
    textColor: 'text-sky-700',
    href: '/employee/catalog/network',
  },
  {
    id: 'software',
    title: 'Phần mềm & license',
    desc: 'Microsoft 365, cài đặt phần mềm được phê duyệt và bảo vệ antivirus',
    icon: KeyRound,
    badge: 'Phần mềm',
    color: 'from-emerald-500 to-teal-600',
    bgColor: 'bg-emerald-50/80',
    borderColor: 'border-emerald-200/80',
    textColor: 'text-emerald-700',
    href: '/employee/catalog/software',
  },
  {
    id: 'accounts',
    title: 'Tài khoản công ty',
    desc: 'Mở khóa tài khoản, email alias hoặc cập nhật tên hiển thị / email',
    icon: KeyRound,
    badge: 'Tài khoản',
    color: 'from-violet-500 to-indigo-600',
    bgColor: 'bg-violet-50/80',
    borderColor: 'border-violet-200/80',
    textColor: 'text-violet-700',
    href: '/employee/catalog/accounts',
  },
  {
    id: 'urgent',
    title: 'Sự cố khẩn cấp',
    desc: 'Máy tính sập nguồn, màn hình xanh BSOD, khóa BitLocker, mã độc',
    icon: AlertOctagon,
    badge: 'Khẩn cấp / BSOD',
    color: 'from-red-500 to-rose-600',
    bgColor: 'bg-rose-50/80',
    borderColor: 'border-rose-200/80',
    textColor: 'text-rose-700',
    href: '/employee/new-ticket?category=REQUEST_TECH_SUPPORT&subject=Sự cố khẩn cấp cần hỗ trợ',
  },
];

const KB_SUGGESTIONS = [
  { title: 'Khắc phục sự cố Wi-Fi trên Windows', category: 'Hạ tầng mạng', link: '/employee/kb' },
  { title: 'Kết nối VPN làm việc từ xa trên Windows', category: 'Hạ tầng mạng', link: '/employee/kb' },
  { title: 'Sửa lỗi tệp dữ liệu Outlook PST và OST', category: 'Phần mềm', link: '/employee/kb' },
  { title: 'Xử lý lỗi tự đặt lại mật khẩu Entra SSPR', category: 'Tài khoản', link: '/employee/kb' },
  { title: 'Khắc phục lỗi màn hình xanh Windows (BSOD)', category: 'Sự cố khẩn cấp', link: '/employee/kb' },
];

export default function EmployeeDashboard() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['my-tickets'],
    queryFn: async () => (await api.get('/tickets?page=1&page_size=12')).data as { items: Ticket[]; total: number },
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });


  const tickets = data?.items ?? [];
  const active = tickets.filter((ticket) => ['open', 'classifying', 'in_progress'].includes(ticket.status)).length;
  const pendingHitl = tickets.filter((ticket) => ticket.status === 'pending_hitl').length;
  const done = tickets.filter((ticket) => ['resolved', 'closed'].includes(ticket.status)).length;

  const filteredKb = KB_SUGGESTIONS.filter((item) =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="employee-dashboard space-y-8">
      
      {/* Golden Zone Central Smart Search Bar */}
      <div className="glass-card-light rounded-3xl p-8 bg-gradient-to-r from-blue-50/60 via-white to-cyan-50/60 border border-slate-200/90 shadow-lg shadow-blue-900/5 relative overflow-hidden">
        <div className="max-w-3xl mx-auto text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full badge-glow-blue text-[12px] font-semibold">
            <span>✨ Golden Zone Smart Search • Multi-Agent RAG</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Xin chào{user?.full_name ? `, ${user.full_name.split(' ').slice(-1)[0]}` : ''}! Bạn cần IT hỗ trợ vấn đề gì hôm nay?
          </h1>
          <p className="text-slate-600 text-sm font-medium">
            Nhập từ khóa tìm kiếm để tra cứu 392+ bài viết tri thức hoặc chọn biểu mẫu gửi yêu cầu bên dưới.
          </p>

          {/* Search Box with Live Dropdown */}
          <div className="relative mt-4 text-left">
            <div className="relative flex items-center">
              <Search className="absolute left-4 text-slate-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Nhập vấn đề của bạn (Ví dụ: Lỗi VPN, Khóa BitLocker, Outlook PST)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                className="w-full pl-12 pr-28 py-3.5 bg-white rounded-2xl border border-slate-300 text-slate-900 placeholder-slate-400 text-sm font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
              <button
                onClick={() => router.push(`/employee/new-ticket?subject=${encodeURIComponent(searchQuery)}`)}
                className="absolute right-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
              >
                <span>Tạo ticket</span>
                <ArrowRight size={14} />
              </button>
            </div>

            {/* Live Dropdown Suggestions */}
            {isFocused && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl border border-slate-200 shadow-2xl z-30 overflow-hidden divide-y divide-slate-100">
                <div className="p-3 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider flex justify-between items-center">
                  <span>Bài viết tri thức KB trùng khớp</span>
                  <span className="text-blue-600">392 KB Docs</span>
                </div>
                {filteredKb.length > 0 ? (
                  filteredKb.map((kb) => (
                    <div
                      key={kb.title}
                      onClick={() => router.push(`/employee/new-ticket?subject=${encodeURIComponent(kb.title)}`)}
                      className="p-3.5 hover:bg-blue-50/60 cursor-pointer flex items-center justify-between transition-colors group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                          KB
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                            {kb.title}
                          </div>
                          <div className="text-[11px] text-slate-500 font-medium">{kb.category}</div>
                        </div>
                      </div>
                      <ExternalLink size={14} className="text-slate-400 group-hover:text-blue-600" />
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-xs text-slate-500">
                    Không tìm thấy bài viết trùng khớp. <button onClick={() => router.push('/employee/new-ticket')} className="text-blue-600 font-bold underline">Tạo ticket mới</button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Service Catalog Card Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Danh Mục Dịch Vụ CNTT (Service Catalog)
            </h2>
            <p className="text-xs text-slate-500 font-medium">Chọn loại hình dịch vụ bạn cần hỗ trợ để chuyển nhanh đến biểu mẫu tương ứng.</p>
          </div>
          <Link href="/employee/catalog" className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1">
            <span>Tất cả biểu mẫu</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {SERVICE_CATALOG.map((cat) => {
            const Icon = cat.icon;
            return (
              <div
                key={cat.id}
                onClick={() => router.push(cat.href)}
                className={`glass-card-light glass-card-light-hover rounded-2xl p-5 border ${cat.borderColor} cursor-pointer flex flex-col justify-between group`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${cat.color} text-white flex items-center justify-center shadow-md`}>
                      <Icon size={20} />
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cat.bgColor} ${cat.textColor}`}>
                      {cat.badge}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors" style={{ fontFamily: 'Outfit, sans-serif' }}>
                    {cat.title}
                  </h3>
                  <p className="text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                    {cat.desc}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-600">
                  <span>Yêu cầu hỗ trợ</span>
                  <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Ticket process overview */}
      <div className="glass-card-light rounded-2xl p-5">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Luồng Xử Lý Ticket Tự Động</div>
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {['1. Tiếp nhận', '2. AI phân loại', '3. RAG tra KB', '4. Duyệt HITL', '5. Đóng ticket'].map((step, idx) => (
              <div key={step} className="flex items-center gap-2 flex-shrink-0">
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${idx === 0 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {step}
                </span>
                {idx < 4 && <span className="text-slate-300 font-bold">→</span>}
              </div>
            ))}
          </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Tổng ticket', value: data?.total ?? 0, icon: Inbox, color: 'text-blue-600', bgColor: 'bg-blue-50' },
          { label: 'Đang xử lý', value: active, icon: Clock3, color: 'text-cyan-600', bgColor: 'bg-cyan-50' },
          { label: 'Chờ duyệt HITL', value: pendingHitl, icon: ShieldCheck, color: 'text-amber-600', bgColor: 'bg-amber-50' },
          { label: 'Đã hoàn tất', value: done, icon: CheckCircle2, color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="glass-card-light rounded-2xl p-5 flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">{stat.label}</div>
                <div className={`text-3xl font-bold mt-1 ${stat.color}`} style={{ fontFamily: 'Outfit, sans-serif' }}>
                  {stat.value}
                </div>
              </div>
              <div className={`w-11 h-11 rounded-xl ${stat.bgColor} ${stat.color} flex items-center justify-center`}>
                <Icon size={22} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Tickets Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Yêu cầu gần đây của bạn
          </h2>
          <Link href="/employee/tickets" className="text-xs font-bold text-blue-600 hover:underline">
            Xem tất cả ticket →
          </Link>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner size={32} /></div>
        ) : tickets.length === 0 ? (
          <div className="glass-card-light rounded-2xl p-8 text-center">
            <EmptyState
              icon="inbox"
              title="Bạn chưa có ticket nào"
              desc="Gửi yêu cầu đầu tiên để AI Agent phân loại và hỗ trợ tức thì."
              action={<Link href="/employee/new-ticket" className="btn-primary">Gửi ticket mới</Link>}
            />
          </div>
        ) : (
          <div className="space-y-3">
            {tickets.slice(0, 5).map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} linkTo={`/employee/tickets/${ticket.id}`} showSla={false} />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
