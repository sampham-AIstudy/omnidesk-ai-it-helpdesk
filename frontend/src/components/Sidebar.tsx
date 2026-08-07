'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
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
  { href: '/employee/sspr', label: 'Tự Reset Mật Khẩu & Access', icon: KeyRound },
  { href: '/employee/kb', label: 'Trung Tâm Tri Thức (KB)', icon: HelpCircle },
  { href: '/employee/new-ticket', label: 'Gửi Yêu Cầu Hỗ Trợ', icon: FilePlus2 },
  { href: '/employee/tickets', label: 'Yêu Cầu Của Tôi & CSAT', icon: ClipboardList },
];

// 2. IT AGENT / TECHNICIAN NAV
const TECH_AGENT_NAV: NavItem[] = [
  { href: '/technician/queue', label: 'Hàng Đợi Ticket (Queue)', icon: Inbox },
  { href: '/manager/changes', label: 'Quản Lý Thay Đổi (Changes)', icon: GitBranch },
  { href: '/manager/problems', label: 'Kho Lỗi Đã Biết (KEDB)', icon: Layers },
  { href: '/employee/tickets', label: 'Tra Cứu Ticket Cá Nhân', icon: TicketCheck },
];

// 3. IT MANAGER / TEAM LEAD NAV
const IT_MANAGER_NAV: NavItem[] = [
  { href: '/manager/dashboard', label: 'Bảng Điều Khiển Quản Lý', icon: Gauge },
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
  { href: '/admin/ai-console', label: 'AI Agentic Console', icon: Cpu },
  { href: '/admin/users', label: 'Quản Lý Phân Quyền RBAC', icon: Users },
  { href: '/admin/cmdb', label: 'Kho Cấu Hình Hạ Tầng CMDB', icon: Laptop },
  { href: '/admin/integrations', label: 'Tích Hợp SSO / Mail / Bot', icon: KeyRound },
  { href: '/admin/kb', label: 'Quản Lý Tri Thức (KB)', icon: BookOpen },
  { href: '/manager/analytics', label: 'Báo Cáo Bảng Giám Sát', icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
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

        <div style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between', width: '100%', padding: '4px 8px 18px' }}>
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

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
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

        <div className="sidebar-status" style={{ border: '1px solid #263247', background: '#152033', borderRadius: 12, padding: 12, marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
            <span className="pulse-dot" />
            <span style={{ color: '#dbeafe', fontSize: 12, fontWeight: 800 }}>Agentic AI Online</span>
          </div>
          <div style={{ color: '#91a1b7', fontSize: 11, lineHeight: 1.45 }}>
            392+ KB Docs • Auto-SSPR Active
          </div>
        </div>

        {user && (
          <div className="sidebar-footer" style={{ borderTop: '1px solid #263247', paddingTop: 12 }}>
            <div className="sidebar-user-card" style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 10, borderRadius: 12, background: '#152033', marginBottom: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 8, background: '#2563eb', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
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


