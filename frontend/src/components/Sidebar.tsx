'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { usePathname, useRouter } from 'next/navigation';
import {
  Activity,
  BarChart3,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  ClipboardCheck,
  ClipboardList,
  FilePlus2,
  Gauge,
  HelpCircle,
  Inbox,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  Package,
  PackageCheck,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  TicketCheck,
  UserCheck,
  UserRound,
  Users,
  X,
} from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';
import { ROLE_LABELS } from '@/lib/utils';
import NotificationCenter from './NotificationCenter';

const AIChatWidget = dynamic(() => import('./AIChatWidget'), {
  ssr: false,
  loading: () => null,
});

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  group?: string;
}

const END_USER_NAV: NavItem[] = [
  { href: '/employee/dashboard', label: 'Cổng tự phục vụ', icon: LayoutDashboard, group: 'Tổng quan' },
  { href: '/employee/chatbot', label: 'Chatbot Workspace', icon: MessageSquareText, group: 'Hỗ trợ' },
  { href: '/employee/new-ticket', label: 'Tạo ticket với AI', icon: FilePlus2 },
  { href: '/employee/tickets', label: 'Sự cố của tôi', icon: TicketCheck },
  { href: '/employee/catalog', label: 'IT Service Catalog', icon: Package, group: 'Dịch vụ' },
  { href: '/employee/requests', label: 'Yêu cầu dịch vụ', icon: ClipboardList },
  { href: '/employee/kb', label: 'Trung tâm tri thức', icon: HelpCircle, group: 'Tài khoản' },
  { href: '/employee/profile', label: 'Hồ sơ & thiết lập', icon: UserRound },
  { href: '/status', label: 'Trạng thái dịch vụ', icon: Activity },
];

const TECH_AGENT_NAV: NavItem[] = [
  { href: '/technician/queue', label: 'Incident queue', icon: Inbox, group: 'Xử lý công việc' },
  { href: '/technician/requests', label: 'Fulfillment workbench', icon: PackageCheck },
];

const IT_MANAGER_NAV: NavItem[] = [
  { href: '/manager/dashboard', label: 'Control tower', icon: Gauge, group: 'Điều hành' },
  { href: '/manager/tickets', label: 'Hàng đợi sự cố', icon: Inbox },
  { href: '/manager/approvals', label: 'HITL approvals', icon: ClipboardCheck, group: 'Quyết định' },
  { href: '/manager/analytics', label: 'Phân tích hiệu suất', icon: BarChart3 },
];

const SYSTEM_ADMIN_NAV: NavItem[] = [
  { href: '/admin/users', label: 'Users & RBAC', icon: Users, group: 'Quản trị hệ thống' },
  { href: '/admin/kb', label: 'Knowledge base', icon: ClipboardList },
  { href: '/admin/ai-review', label: 'AI review queue', icon: UserCheck, group: 'AI Governance' },
  { href: '/admin/ai-evaluation', label: 'Evaluation & benchmarks', icon: BarChart3 },
  { href: '/admin/rag', label: 'RAG pipeline', icon: BookOpen },
  { href: '/admin/token-usage', label: 'Token & Cost', icon: CircleDollarSign, group: 'Billing & Usage' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [quickQuery, setQuickQuery] = useState('');
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);
  const [aiChatStarted, setAiChatStarted] = useState(false);
  const [aiChatOpen, setAiChatOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const quickSearchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('omni_sidebar_collapsed');
      if (saved === 'true') {
        setCollapsed(true);
        document.querySelector('.main-content')?.classList.add('collapsed');
      }
    } catch {}
  }, []);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem('omni_sidebar_collapsed', String(next));
    } catch {}
    const main = document.querySelector('.main-content');
    if (next) {
      main?.classList.add('collapsed');
    } else {
      main?.classList.remove('collapsed');
    }
  };

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
      ? END_USER_NAV.filter((item) => item.href !== '/employee/profile')
      : user?.role === 'technician'
      ? TECH_AGENT_NAV
      : user?.role === 'admin'
      ? SYSTEM_ADMIN_NAV
      : IT_MANAGER_NAV;

  const quickMatches = useMemo(() => {
    const query = quickQuery.trim().toLocaleLowerCase('vi-VN');
    if (!query) return navItems.slice(0, 5);
    return navItems.filter((item) => item.label.toLocaleLowerCase('vi-VN').includes(query)).slice(0, 6);
  }, [navItems, quickQuery]);

  const navigateFromQuickSearch = (href: string) => {
    router.push(href);
    setQuickQuery('');
    setQuickSearchOpen(false);
    setMobileOpen(false);
  };

  useEffect(() => {
    const focusQuickSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setMobileOpen(true);
        setQuickSearchOpen(true);
        window.setTimeout(() => quickSearchRef.current?.focus(), 0);
      }
      if (event.key === 'Escape' && document.activeElement === quickSearchRef.current) {
        setQuickQuery('');
        setQuickSearchOpen(false);
        quickSearchRef.current?.blur();
      }
    };
    window.addEventListener('keydown', focusQuickSearch);
    return () => window.removeEventListener('keydown', focusQuickSearch);
  }, []);

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
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`} aria-label="Điều hướng chính">
        <button className="sidebar-close" onClick={() => setMobileOpen(false)} aria-label="Đóng menu điều hướng">
          <X size={20} aria-hidden="true" />
        </button>

        {/* Floating edge toggle protruding on the right border */}
        <button
          type="button"
          onClick={toggleCollapsed}
          className="sidebar-edge-toggle"
          title={collapsed ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'}
          aria-label={collapsed ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>

        <div className="sidebar-brand">
          <div className="sidebar-brand-mark" title="OmniDesk.AI">
            AI
          </div>
          <div className="sidebar-brand-copy">
            <div>OmniDesk.AI</div>
            <div>
              {user?.role === 'admin' ? 'Super Admin Console' : user?.role === 'manager' ? 'IT Manager Tower' : user?.role === 'technician' ? 'IT Agent Workbench' : 'End-User Portal'}
            </div>
          </div>
        </div>

        <div className="sidebar-quick-search">
          <div className="sidebar-quick-search-input">
            <Search size={13} aria-hidden="true" />
            <input
              ref={quickSearchRef}
              type="search"
              value={quickQuery}
              onChange={(event) => {
                setQuickQuery(event.target.value);
                setQuickSearchOpen(true);
              }}
              onFocus={() => setQuickSearchOpen(true)}
              onBlur={() => window.setTimeout(() => setQuickSearchOpen(false), 120)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && quickMatches[0]) {
                  event.preventDefault();
                  navigateFromQuickSearch(quickMatches[0].href);
                }
              }}
              placeholder="Tìm nhanh…"
              aria-label="Tìm trang hoặc thao tác nhanh"
              aria-controls="sidebar-quick-search-results"
              className="sidebar-quick-search-field"
            />
            <kbd>Ctrl + K</kbd>
          </div>

          {quickSearchOpen && (
            <div id="sidebar-quick-search-results" className="sidebar-quick-results">
              {quickMatches.length > 0 ? quickMatches.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => navigateFromQuickSearch(item.href)}
                    className="sidebar-quick-result"
                  >
                    <span className="sidebar-quick-result-icon" aria-hidden="true"><Icon size={14} /></span>
                    <span>{item.label}</span>
                  </button>
                );
              }) : (
                <p className="px-2.5 py-3 text-xs text-slate-400">Không tìm thấy mục phù hợp.</p>
              )}
            </div>
          )}
        </div>

        <nav className="sidebar-navigation" aria-label="Điều hướng portal">
          {navItems.map((item, index) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}`));
            return (
              <div key={item.href}>
                {item.group && (index === 0 || navItems[index - 1]?.group !== item.group) && <div className="sidebar-nav-group">{item.group}</div>}
                <Link href={item.href} prefetch className={`sidebar-nav-item ${active ? 'active' : ''}`} aria-current={active ? 'page' : undefined} onClick={() => setMobileOpen(false)}>
                  <Icon size={17} aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              </div>
            );
          })}
        </nav>

        {user && (
          <div className="sidebar-footer">
            <Link
              href={user.role === 'employee' ? '/employee/profile' : user.role === 'technician' ? '/technician/queue' : user.role === 'manager' ? '/manager/dashboard' : '/admin/ai-review'}
              className="sidebar-user-card"
              style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 8, borderRadius: 12, marginBottom: 8, color: 'inherit', textDecoration: 'none' }}
              title={collapsed ? `${user.full_name} (${ROLE_LABELS[user.role]})` : 'Mở hồ sơ cá nhân'}
            >
              <div className="sidebar-user-avatar">
                {user.full_name.slice(0, 1)}
              </div>
              <div className="sidebar-user-copy">
                <div>
                  {user.full_name}
                </div>
                <div>
                  {ROLE_LABELS[user.role]}
                </div>
              </div>
              {user.role === 'employee' && <Settings className="sidebar-profile-shortcut" size={16} aria-hidden="true" />}
            </Link>

            <button
              onClick={logout}
              className="btn-ghost sidebar-logout"
              title="Đăng xuất khỏi hệ thống"
            >
              <LogOut size={15} />
              <span>Đăng xuất</span>
            </button>
          </div>
        )}
      </aside>
      {pathname !== '/employee/chatbot' && !aiChatOpen && (
        <button
          type="button"
          onClick={() => {
            setAiChatStarted(true);
            setAiChatOpen(true);
          }}
          className="ai-copilot-launcher"
          aria-label="Mở AI Copilot"
        >
          <MessageSquareText size={17} aria-hidden="true" />
          AI Copilot
        </button>
      )}
      {pathname !== '/employee/chatbot' && aiChatStarted && <AIChatWidget open={aiChatOpen} showLauncher={false} onOpenChange={setAiChatOpen} />}
    </>
  );
}
