'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import NotificationCenter from '@/components/NotificationCenter';
import { Spinner } from '@/components/ui';
import { useAuthStore } from '@/lib/authStore';
import type { UserRole } from '@/types';

const HOME_BY_ROLE: Record<UserRole, string> = {
  employee: '/employee/dashboard',
  technician: '/technician/queue',
  admin: '/admin/ai-review',
};

const PORTAL_LABEL: Record<UserRole, string> = {
  employee: 'Employee Support',
  technician: 'Agent Workspace',
  admin: 'System Administration',
};

type PortalShellProps = {
  allowedRoles: UserRole[];
  children: React.ReactNode;
};

/** Shared client-side session and RBAC guard for every private portal. */
export default function PortalShell({ allowedRoles, children }: PortalShellProps) {
  const { user, hydrated, hydrate } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!allowedRoles.includes(user.role)) {
      router.replace(HOME_BY_ROLE[user.role]);
    }
  }, [allowedRoles, hydrated, router, user]);

  if (!hydrated || !user || !allowedRoles.includes(user.role)) {
    return (
      <div className="portal-loading" role="status" aria-label="Đang kiểm tra quyền truy cập">
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <main id="main-content" className="main-content">
        <header className="app-header">
          <div className="app-header-context">
            <span>{PORTAL_LABEL[user.role]}</span>
            <span aria-hidden="true">/</span>
            <strong>{pathname.split('/').filter(Boolean).at(-1)?.replace(/-/g, ' ') || 'overview'}</strong>
          </div>
          <NotificationCenter />
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
