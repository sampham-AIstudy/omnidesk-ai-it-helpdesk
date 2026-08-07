'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useAuthStore } from '@/lib/authStore';
import { Spinner } from '@/components/ui';

export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  const { user, hydrate } = useAuthStore();
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    hydrate();
    setHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !user) {
      router.replace('/login');
    }
  }, [hydrated, user, router]);

  if (!hydrated || !user) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">{children}</main>
    </div>
  );
}

