'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  ClipboardList,
  FilePlus2,
  Gauge,
  Inbox,
  Menu,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  TicketCheck,
  Users,
  Wrench,
  X,
  Zap,
  Clock,
  Tv,
  Laptop,
  KeyRound,
  GitBranch,
  Layers,
  Siren,
  Cpu,
  Bot,
  HelpCircle,
  PackageCheck,
  Bell,
  Network,
  Calendar,
  Building2,
  Activity,
  UserCheck,
  Search,
  Package,
} from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';
import { ROLE_LABELS } from '@/lib/utils';
import NotificationCenter from './NotificationCenter';
import AIChatWidget from './AIChatWidget';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}

// 1. END-USER PORTAL NAV
const END_USER_NAV: NavItem[] = [
  { href: '/employee/dashboard', label: 'Cổng Tự Phục Vụ', icon: LayoutDashboard },
  { href: '/employee/catalog', label: 'IT Service Catalog (Yêu Cầu)', icon: Package },
  { href: '/employee/requests', label: 'Yêu Cầu Dịch Vụ Của Tôi', icon: ClipboardList },
  { href: '/employee/tickets', label: 'Sự Cố Của Tôi & CSAT', icon: TicketCheck },
  { href: '/employee/new-ticket', label: 'Gửi Sự Cố Hỗ Trợ', icon: FilePlus2 },
  { href: '/employee/sspr', label: 'Tự Reset Mật Khẩu & Access', icon: KeyRound },
  { href: '/employee/kb', label: 'Trung Tâm Tri Thức (KB)', icon: HelpCircle },
];

// 2. IT AGENT / TECHNICIAN NAV
const TECH_AGENT_NAV: NavItem[] = [
  { href: '/technician/queue', label: 'Hàng Đợi Incident Queue', icon: Inbox },
  { href: '/technician/requests', label: 'Fulfillment Workbench (REQ)', icon: PackageCheck },
  { href: '/technician/alerts', label: 'Alert / Event Console (Monitoring)', icon: Bell },
  { href: '/technician/on-call', label: 'Lịch Trực On-Call & Escalation', icon: Clock },
  { href: '/manager/changes', label: 'Quản Lý Thay Đổi (Changes)', icon: GitBranch },
  { href: '/manager/problems', label: 'Kho Lỗi Đã Biết (KEDB)', icon: Layers },
  { href: '/employee/tickets', label: 'Tra Cứu Ticket Cá Nhân', icon: TicketCheck },
];

// 3. IT MANAGER / TEAM LEAD NAV
const IT_MANAGER_NAV: NavItem[] = [
  { href: '/manager/dashboard', label: 'Bảng Điều Khiển Quản Lý', icon: Gauge },
  { href: '/manager/services', label: 'Service Portfolio & Sức Khỏe', icon: Activity },
  { href: '/manager/change-calendar', label: 'Change Calendar & CAB', icon: Calendar },
  { href: '/manager/major-incidents', label: 'War Room Sự Cố P1', icon: Siren },
  { href: '/manager/changes', label: 'Quản Lý Thay Đổi ITIL', icon: GitBranch },
  { href: '/manager/problems', label: 'Quản Lý Vấn Đề (KEDB)', icon: Layers },
  { href: '/manager/automation', label: 'Tự Động Hóa Workflow', icon: Zap },
  { href: '/manager/sla-matrix', label: 'Ma Trận Cam Kết SLA', icon: Clock },
  { href: '/manager/wallboard', label: 'Real-Time Wallboard TV', icon: Tv },
  { href: '/manager/analytics', label: 'Phân Tích Hiệu Suất', icon: BarChart3 },
];

// 4. SYSTEM ADMINISTRATOR (SUPER ADMIN) NAV
const SYSTEM_ADMIN_NAV: NavItem[] = [
  { href: '/admin/ai-review', label: 'AI Review Queue (HITL)', icon: UserCheck },
  { href: '/admin/ai-evaluation', label: 'AI Evaluation & Benchmarks', icon: BarChart3 },
  { href: '/admin/rag', label: 'RAG Pipeline & Retrieval Test', icon: BookOpen },
  { href: '/admin/ai-console', label: 'AI Agentic Console', icon: Cpu },
  { href: '/admin/cmdb/map', label: 'CMDB Topology Map', icon: Network },
  { href: '/admin/cmdb', label: 'Kho Cấu Hình CMDB List', icon: Laptop },
  { href: '/admin/organizations', label: 'Quản Lý Tập Đoàn & Tenant', icon: Building2 },
  { href: '/admin/system-health', label: 'System Health & Jobs', icon: Activity },
  { href: '/admin/users', label: 'Quản Lý Phân Quyền RBAC', icon: Users },
  { href: '/admin/integrations', label: 'Tích Hợp SSO / Mail / Bot', icon: KeyRound },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loginAsRole, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    const onKeyDown = (event: KeyboardEvent) => event.key === 'Escape' && setMobileOpen(false);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [mobileOpen]);

  const navItems =
    user?.role === 'employee'
      ? END_USER_NAV
      : user?.role === 'technician'
      ? TECH_AGENT_NAV
      : user?.role === 'admin'
      ? SYSTEM_ADMIN_NAV
      : IT_MANAGER_NAV;

  const handleRoleSwitch = (role: 'employee' | 'technician' | 'manager' | 'admin') => {
    loginAsRole(role);
    const targetRoute =
      role === 'employee'
        ? '/employee/dashboard'
        : role === 'technician'
        ? '/technician/queue'
        : role === 'manager'
        ? '/manager/dashboard'
        : '/admin/ai-review';
    router.push(targetRoute);
  };

  return (
    <>
      <header className="mobile-app-header">
        <button className="mobile-menu-button" onClick={() => setMobileOpen(true)} aria-label="Mở menu điều hướng" aria-expanded={mobileOpen}>
          <Menu size={21} aria-hidden="true" />
        </button>
        <div className="flex items-center gap-3">
          <strong>OmniDesk AI</strong>
          <NotificationCenter />
        </div>
      </header>
      {mobileOpen && <button className="sidebar-backdrop" aria-label="Đóng menu điều hướng" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`} aria-label="Điều hướng chính">
        <button className="sidebar-close" onClick={() => setMobileOpen(false)} aria-label="Đóng menu điều hướng">
          <X size={20} aria-hidden="true" />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between', width: '100%', padding: '4px 8px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 38, height: 38, borderRadius: 12, background: 'linear-gradient(135deg, #2563eb, #06b6d4)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
              AI
            </div>
            <div>
              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: 15, fontFamily: 'Outfit, sans-serif' }}>OmniDesk.AI</div>
              <div style={{ color: '#8fa0b7', fontSize: 11, fontWeight: 700 }}>
                {user?.role === 'admin' ? 'Super Admin Console' : user?.role === 'manager' ? 'IT Manager Tower' : user?.role === 'technician' ? 'IT Agent Workbench' : 'End-User Portal'}
              </div>
            </div>
          </div>

          <div className="ml-auto">
            <NotificationCenter />
          </div>
        </div>

        {/* Global Command Palette Hint */}
        <button
          type="button"
          onClick={() => {
            const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
            window.dispatchEvent(event);
          }}
          className="mx-2 mb-3 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-300 flex items-center justify-between font-mono hover:bg-cyan-400/20 transition cursor-pointer"
        >
          <span className="flex items-center gap-1.5">
            <Search size={13} />
            <span>Search...</span>
          </span>
          <span className="rounded bg-black/40 px-1.5 py-0.5 text-[10px]">Ctrl + K</span>
        </button>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, overflowY: 'auto' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}`));
            return (
              <Link key={item.href} href={item.href} className={`sidebar-nav-item ${active ? 'active' : ''}`} aria-current={active ? 'page' : undefined} onClick={() => setMobileOpen(false)}>
                <Icon size={17} aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Demo Role Switcher Bar */}
        <div className="mt-3 mb-2 p-2 rounded-xl border border-white/10 bg-black/40">
          <span className="font-mono text-[9px] text-white/40 uppercase block mb-1 px-1">DEMO ROLE SWITCHER</span>
          <div className="grid grid-cols-4 gap-1 text-[10px] font-mono">
            <button
              type="button"
              onClick={() => handleRoleSwitch('employee')}
              className={`py-1 rounded text-center cursor-pointer transition ${user?.role === 'employee' ? 'bg-cyan-500 text-black font-bold' : 'text-white/60 hover:text-white bg-white/5'}`}
            >
              User
            </button>
            <button
              type="button"
              onClick={() => handleRoleSwitch('technician')}
              className={`py-1 rounded text-center cursor-pointer transition ${user?.role === 'technician' ? 'bg-cyan-500 text-black font-bold' : 'text-white/60 hover:text-white bg-white/5'}`}
            >
              Tech
            </button>
            <button
              type="button"
              onClick={() => handleRoleSwitch('manager')}
              className={`py-1 rounded text-center cursor-pointer transition ${user?.role === 'manager' ? 'bg-cyan-500 text-black font-bold' : 'text-white/60 hover:text-white bg-white/5'}`}
            >
              Mgr
            </button>
            <button
              type="button"
              onClick={() => handleRoleSwitch('admin')}
              className={`py-1 rounded text-center cursor-pointer transition ${user?.role === 'admin' ? 'bg-cyan-500 text-black font-bold' : 'text-white/60 hover:text-white bg-white/5'}`}
            >
              Admin
            </button>
          </div>
        </div>

        {user && (
          <div className="sidebar-footer" style={{ borderTop: '1px solid #263247', paddingTop: 8 }}>
            <div className="sidebar-user-card" style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 8, borderRadius: 12, background: '#152033', marginBottom: 8 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: '#2563eb', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
                {user.full_name.slice(0, 1)}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: '#ffffff', fontSize: 13, fontWeight: 800, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.full_name}
                </div>
                <div style={{ color: '#91a1b7', fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {ROLE_LABELS[user.role]}
                </div>
              </div>
            </div>
            <button onClick={logout} className="btn-ghost" style={{ width: '100%', background: '#101827', borderColor: '#263247', color: '#dce3ee' }}>
              <LogOut size={15} />
              Đăng xuất
            </button>
          </div>
        )}
      </aside>
      <AIChatWidget />
    </>
  );
}
