'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  ClipboardList,
  FilePlus2,
  Gauge,
  History,
  Inbox,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  TicketCheck,
  Users,
  Wrench,
} from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';
import { COMPANY_LABELS, ROLE_LABELS } from '@/lib/utils';
import AIChatWidget from './AIChatWidget';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}

const EMPLOYEE_NAV: NavItem[] = [
  { href: '/employee/dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { href: '/employee/new-ticket', label: 'Gửi ticket', icon: FilePlus2 },
  { href: '/employee/tickets', label: 'Ticket của tôi', icon: ClipboardList },
];

const TECH_NAV: NavItem[] = [
  { href: '/technician/queue', label: 'Hàng đợi xử lý', icon: Inbox },
  { href: '/technician/all', label: 'Toàn bộ ticket', icon: TicketCheck },
];

const MANAGER_NAV: NavItem[] = [
  { href: '/manager/dashboard', label: 'Control tower', icon: Gauge },
  { href: '/manager/approvals', label: 'Duyệt HITL', icon: ShieldCheck },
  { href: '/manager/analytics', label: 'Hiệu suất AI', icon: BarChart3 },
  { href: '/manager/audit', label: 'Audit log', icon: History },
  { href: '/admin/users', label: 'Người dùng', icon: Users },
  { href: '/admin/kb', label: 'Knowledge base', icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  const navItems =
    user?.role === 'employee' ? EMPLOYEE_NAV :
    user?.role === 'technician' ? TECH_NAV :
    MANAGER_NAV;

  return (
    <>
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 18px' }}>
          <div style={{ width: 38, height: 38, borderRadius: 8, background: '#e8f0ff', color: '#174ea6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Wrench size={20} />
          </div>
          <div>
            <div style={{ color: '#ffffff', fontWeight: 800, fontSize: 14 }}>IT Help Desk</div>
            <div style={{ color: '#8fa0b7', fontSize: 11, fontWeight: 700 }}>Agent Workspace</div>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href} className={`sidebar-nav-item ${active ? 'active' : ''}`}>
                <Icon size={17} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-status" style={{ border: '1px solid #263247', background: '#152033', borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
            <span className="pulse-dot" />
            <span style={{ color: '#dbeafe', fontSize: 12, fontWeight: 800 }}>Agent online</span>
          </div>
          <div style={{ color: '#91a1b7', fontSize: 11, lineHeight: 1.45 }}>
            Classifier, RAG, HITL, Router và SLA monitor đang hoạt động.
          </div>
        </div>

        {user && (
          <div className="sidebar-footer" style={{ borderTop: '1px solid #263247', paddingTop: 12 }}>
            <div className="sidebar-user-card" style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 10, borderRadius: 8, background: '#152033', marginBottom: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 8, background: '#ffffff', color: '#101827', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
                {user.full_name.slice(0, 1)}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: '#ffffff', fontSize: 13, fontWeight: 800, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.full_name}
                </div>
                <div style={{ color: '#91a1b7', fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {ROLE_LABELS[user.role]} · {COMPANY_LABELS[user.company_unit] ?? user.company_unit}
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
