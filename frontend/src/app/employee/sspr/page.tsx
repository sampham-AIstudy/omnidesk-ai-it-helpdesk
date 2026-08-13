'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui';

/** Legacy bookmark compatibility. Identity settings now live in Profile. */
export default function LegacySsprPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/employee/profile?section=security');
  }, [router]);

  return <div className="portal-loading"><Spinner size={24} /></div>;
}
