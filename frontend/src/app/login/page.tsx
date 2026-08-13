'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UserRound,
  Wrench,
  ShieldCheck,
  Users,
  Lock,
  Eye,
  EyeOff,
  CircleAlert,
  Loader2,
  ChevronRight,
  Home,
  ArrowLeft,
} from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';
import api from '@/lib/api';

type RoleTab = 'employee' | 'technician' | 'manager' | 'admin';

interface DemoAccount {
  username: string;
  password: string;
  name: string;
  hint: string;
}

const ACCOUNTS: Record<RoleTab, DemoAccount[]> = {
  employee: [
    { username: 'employee1', password: 'demo123', name: 'Nguyễn Văn An', hint: 'Phòng Kế Toán / Sales' },
    { username: 'employee_vip', password: 'demo123', name: 'Trần Thị Bích', hint: 'Ban Giám Đốc / VIP User' },
  ],
  technician: [
    { username: 'tech1', password: 'demo123', name: 'Lê Minh Công', hint: 'IT Support Level 1 & 2' },
  ],
  manager: [
    { username: 'manager1', password: 'demo123', name: 'Phạm Thị Dung', hint: 'Trưởng Phòng IT / Team Lead' },
  ],
  admin: [
    { username: 'admin', password: 'admin123', name: 'System Admin', hint: 'Quản Trị Hệ Thống / Super Admin' },
  ],
};

const ROLE_META: Record<RoleTab, { keyLabel: string; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }> = {
  employee: { keyLabel: 'ROLE 01 — END-USER', label: 'End-User', icon: UserRound },
  technician: { keyLabel: 'ROLE 02 — IT AGENT', label: 'IT Agent', icon: Wrench },
  manager: { keyLabel: 'ROLE 03 — IT MANAGER', label: 'IT Manager', icon: ShieldCheck },
  admin: { keyLabel: 'ROLE 04 — SYSTEM ADMIN', label: 'System Admin', icon: Users },
};

const ROLE_CARDS = [
  {
    icon: UserRound,
    title: 'End-User',
    tag: 'ROLE 01',
    text: 'Tạo ticket, tra cứu kiến thức KB, đóng phiếu & đánh giá 5★ CSAT.',
  },
  {
    icon: Wrench,
    title: 'IT Agent',
    tag: 'ROLE 02',
    text: 'Xử lý Queue ticket, xem IT Asset Widget, viết phản hồi công khai / ghi chú nội bộ.',
  },
  {
    icon: ShieldCheck,
    title: 'IT Manager',
    tag: 'ROLE 03',
    text: 'Điều phối ticket, xem Wallboard TV, cấu hình Workflow Automation & Ma trận SLA.',
  },
  {
    icon: Users,
    title: 'System Admin',
    tag: 'ROLE 04',
    text: 'Quản trị tối cao, phân quyền RBAC, quản lý CMDB & tích hợp SSO/Bot.',
  },
];

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);

  const [activeTab, setActiveTab] = useState<RoleTab>('employee');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    document.title = 'Help Desk ITSM | Đăng Nhập';
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');
      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          redirectUser(user.role);
        } catch {
          // ignore invalid token in local storage
        }
      }
    }
  }, []);

  const redirectUser = (role: string) => {
    if (role === 'employee') router.push('/employee/dashboard');
    else if (role === 'technician') router.push('/technician/queue');
    else if (role === 'admin') router.push('/admin/users');
    else router.push('/manager/dashboard');
  };

  const handleLogin = async (u: string, p: string) => {
    if (!u || !p) return;
    setIsLoading(true);
    setErrorMessage('');

    try {
      const response = await api.post('/auth/login', { username: u, password: p });
      const data = response.data;
      setAuth(data.user, data.access_token);
      redirectUser(data.user.role);
    } catch (err: any) {
      if (err.response?.status >= 400 && err.response?.status < 500) {
        setErrorMessage('Tên đăng nhập hoặc mật khẩu không đúng.');
      } else {
        setErrorMessage('Không thể kết nối máy chủ. Vui lòng thử lại.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const submitForm = (e: React.FormEvent) => {
    e.preventDefault();
    handleLogin(username, password);
  };

  const handleDemoClick = (acc: DemoAccount) => {
    setUsername(acc.username);
    setPassword(acc.password);
    handleLogin(acc.username, acc.password);
  };

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-900 selection:bg-blue-600 selection:text-white grid lg:grid-cols-[1.1fr_1fr] relative overflow-hidden font-sans">
      {/* Background radial glow accents */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-blue-100/50 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 left-1/3 w-80 h-80 bg-cyan-100/50 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* LEFT PANEL — Architecture intro */}
      <section className="hidden lg:flex flex-col justify-between px-12 xl:px-16 py-12 relative z-10 border-r border-slate-300/80 bg-white/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          {/* Top Brand Badge & Back to Home */}
          <div className="flex items-center justify-between gap-4 w-full">
            <div className="rounded-xl border border-slate-300 bg-white shadow-sm px-4 py-2 inline-flex gap-2.5 items-center w-fit">
              <span className="size-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="font-mono text-xs uppercase tracking-wider text-slate-800 font-bold">
                Enterprise IT Help Desk Architecture
              </span>
              <span className="border border-blue-300 text-blue-800 bg-blue-100/90 rounded-full px-3 py-1 font-mono text-[11px] tracking-wider font-bold">
                4 Distinct Roles
              </span>
            </div>

            <Link
              href="/"
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 shadow-xs hover:shadow-sm transition-all group shrink-0"
              title="Về Trang Chủ"
            >
              <Home size={15} className="text-blue-600 group-hover:scale-110 transition-transform" />
              <span>Về trang chủ</span>
            </Link>
          </div>

          {/* Heading */}
          <h1 className="text-4xl xl:text-5xl font-bold leading-tight text-slate-900 max-w-xl mt-8 tracking-tight">
            Hệ Thống Help Desk Phân Quyền{' '}
            <span className="bg-gradient-to-r from-blue-700 via-blue-600 to-cyan-600 bg-clip-text text-transparent">
              4 Vai Trò Chuẩn ITSM
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mt-4 text-slate-700 leading-relaxed max-w-lg text-base font-medium">
            Một hệ thống hỗ trợ tập trung cho 4 nhóm vai trò doanh nghiệp — từ tiếp nhận yêu cầu, xử lý kỹ thuật đến giám sát vận hành và quản trị toàn hệ thống.
          </p>

          {/* Role Grid */}
          <div className="mt-10 grid sm:grid-cols-2 gap-4">
            {ROLE_CARDS.map((card, idx) => {
              const Icon = card.icon;
              return (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 * (idx + 1), ease: 'easeOut' }}
                  className="group rounded-2xl border border-slate-300 bg-white p-5.5 shadow-sm hover:border-blue-500 hover:shadow-md hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="size-11 rounded-xl bg-blue-100/80 text-blue-700 flex items-center justify-center font-bold">
                      <Icon size={22} strokeWidth={2} />
                    </div>
                    <span className="font-mono uppercase text-[10px] tracking-wider text-blue-800 bg-blue-100 border border-blue-300 px-2.5 py-1 rounded-md font-bold">
                      {card.tag}
                    </span>
                  </div>
                  <h3 className="text-slate-900 font-bold text-lg">{card.title}</h3>
                  <p className="text-slate-700 text-sm leading-relaxed mt-2 font-medium">{card.text}</p>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Footer Left */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="pt-8 mt-12 border-t border-slate-300 flex justify-between items-center text-slate-600 text-xs font-mono font-semibold"
        >
          <span>© 2026 Help Desk ITSM</span>
          <span className="uppercase tracking-wider text-[11px] font-bold">v2.0.1</span>
        </motion.footer>
      </section>

      {/* RIGHT PANEL — Login form */}
      <section className="flex flex-col items-center justify-center px-6 sm:px-10 py-12 relative z-10">
        {/* Mobile Brand Bar */}
        <div className="lg:hidden mb-8 w-full max-w-md flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-wider text-slate-800 font-bold">
              Enterprise IT Help Desk
            </span>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 shadow-xs transition-all"
          >
            <Home size={14} className="text-blue-600" />
            <span>Về trang chủ</span>
          </Link>
        </div>

        {/* Glass Card Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="w-full max-w-md rounded-3xl border border-slate-300 bg-white p-6 sm:p-8 shadow-2xl shadow-slate-300/40"
        >
          {/* Card Header */}
          <div>
            <span className="font-mono uppercase text-xs tracking-wider text-blue-700 font-extrabold block mb-1">
              SECURE ACCESS
            </span>
            <h2 className="text-2xl font-extrabold text-slate-900">Đăng Nhập Hệ Thống</h2>
            <p className="text-sm text-slate-600 font-medium mt-1">Chọn vai trò hoặc nhập thông tin tài khoản để tiếp tục.</p>
          </div>

          {/* Role Tabs */}
          <div className="mt-6 grid grid-cols-4 gap-2">
            {(Object.keys(ROLE_META) as RoleTab[]).map((role) => {
              const Icon = ROLE_META[role].icon;
              const isActive = activeTab === role;
              return (
                <button
                  key={role}
                  type="button"
                  onClick={() => setActiveTab(role)}
                  className={`flex flex-col items-center gap-1.5 rounded-xl border px-2 py-3 transition-all duration-300 cursor-pointer ${
                    isActive
                      ? 'border-2 border-blue-600 bg-blue-50 text-blue-800 font-bold shadow-sm'
                      : 'border border-slate-300 bg-slate-100/70 text-slate-700 font-semibold hover:border-slate-400 hover:bg-slate-200/80 hover:text-slate-900'
                  }`}
                >
                  <Icon size={20} />
                  <span className="text-[11px] truncate w-full text-center">
                    {ROLE_META[role].label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active Role Indicator */}
          <div className="font-mono uppercase text-xs tracking-wider text-slate-600 font-bold mt-2.5 text-right">
            {ROLE_META[activeTab].keyLabel}
          </div>

          {/* Demo Accounts List */}
          <div className="mt-5">
            <div className="font-mono uppercase text-xs tracking-wider text-slate-700 font-extrabold mb-2.5">
              TÀI KHOẢN DEMO · ĐĂNG NHẬP 1-CLICK
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="space-y-2.5"
              >
                {ACCOUNTS[activeTab].map((acc) => (
                  <button
                    key={acc.username}
                    type="button"
                    onClick={() => handleDemoClick(acc)}
                    disabled={isLoading}
                    className="w-full flex items-center justify-between gap-3 rounded-xl border border-slate-300 bg-slate-50 hover:border-blue-500 hover:bg-blue-50/70 px-4 py-3.5 transition-all duration-300 group text-left cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-900 font-bold font-mono">{acc.username}</span>
                        <span className="text-xs text-slate-800 font-semibold truncate">• {acc.name}</span>
                      </div>
                      <span className="text-xs text-slate-600 font-medium truncate">{acc.hint}</span>
                    </div>
                    <ChevronRight size={16} className="text-slate-500 group-hover:text-blue-700 transition-colors shrink-0" />
                  </button>
                ))}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Divider */}
          <div className="mt-6 flex items-center gap-4">
            <div className="h-px flex-1 bg-slate-300" />
            <span className="font-mono uppercase text-xs tracking-wider text-slate-600 font-bold">
              HOẶC NHẬP THỦ CÔNG
            </span>
            <div className="h-px flex-1 bg-slate-300" />
          </div>

          {/* Manual Form */}
          <form onSubmit={submitForm} className="mt-6 space-y-4">
            <div>
              <label className="block mb-1.5 text-xs font-bold text-slate-800">Tên đăng nhập</label>
              <div className="relative">
                <UserRound size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="username"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/80 pl-10 pr-4 py-3 text-sm text-slate-900 font-semibold placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20 transition font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block mb-1.5 text-xs font-bold text-slate-800">Mật khẩu</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/80 pl-10 pr-10 py-3 text-sm text-slate-900 font-semibold placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20 transition font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-xs text-red-800 font-bold flex gap-2 items-center"
                >
                  <CircleAlert size={14} className="shrink-0" />
                  <span>{errorMessage}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !username || !password}
              className="mt-2 w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-base py-3.5 shadow-lg shadow-blue-600/30 active:scale-[0.98] transition-all duration-300 disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : (
                <span>Đăng Nhập Ngay</span>
              )}
            </button>
          </form>

          {/* Footer Right Note */}
          <p className="mt-6 text-center text-xs text-slate-600 font-medium">
            Đăng nhập bằng tài khoản demo giúp trải nghiệm nhanh từng vai trò.
            <span className="font-mono text-slate-700 font-bold block mt-1 tracking-wider">DEMO123</span>
          </p>
        </motion.div>
      </section>
    </main>
  );
}
