'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';

export default function RootPage() {
  const router = useRouter();
  const { user, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!user) { router.replace('/login'); return; }
    if (user.role === 'employee')   router.replace('/employee/dashboard');
    if (user.role === 'technician') router.replace('/technician/queue');
    if (user.role === 'manager')    router.replace('/manager/dashboard');
    if (user.role === 'admin')      router.replace('/manager/dashboard');
  }, [user, router]);

  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:'100vh' }}>
      <div className="spin" style={{ width:32, height:32, border:'3px solid rgba(99,102,241,0.3)', borderTopColor:'#6366f1', borderRadius:'50%' }} />
    </div>
  );
}
