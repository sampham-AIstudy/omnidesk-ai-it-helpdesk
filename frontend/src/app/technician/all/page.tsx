'use client';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function TechAllRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/technician/queue'); }, [router]);
  return null;
}
