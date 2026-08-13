'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/lib/authStore';
import LandingNavbar from '@/components/landing/LandingNavbar';
import LandingHero2026 from '@/components/landing/LandingHero2026';
import MarqueeScroller from '@/components/landing/MarqueeScroller';
import LandingFeatures from '@/components/landing/LandingFeatures';
import { Spinner } from '@/components/ui';

export default function RootPage() {
  const hydrate = useAuthStore((state) => state.hydrate);
  const hydrated = useAuthStore((state) => state.hydrated);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  if (!hydrated) {
    return (
      <div className="public-app-page flex items-center justify-center min-h-screen bg-[#f9fafb]">
        <Spinner size={34} />
      </div>
    );
  }

  // Next-Gen 2026 Landing Page (#f9fafb background)
  return (
    <div className="public-app-page min-h-screen bg-[#f9fafb] text-slate-900 selection:bg-cyan-300 selection:text-slate-950">
      <LandingNavbar />
      <main className="pb-16">
        <LandingHero2026 />
        <MarqueeScroller />
        <LandingFeatures />
      </main>
      
      {/* Light Theme Footer */}
      <footer className="py-12 px-6 border-t border-slate-200/60 bg-white text-center">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 text-white font-bold flex items-center justify-center text-xs">
              AI
            </div>
            <span className="font-bold text-slate-900 text-sm tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              OmniDesk.AI — Enterprise Agentic IT Help Desk
            </span>
          </div>
          <p className="text-xs text-slate-500 font-medium">
            © 2026 OmniDesk AI Platform. Multi-Agent RAG Engine powered by Mistral & ChromaDB.
          </p>
          <div className="flex items-center gap-6 text-xs font-semibold text-slate-600">
            <Link href="/login" className="hover:text-blue-600 transition-colors">Đăng nhập</Link>
            <Link href="/status" className="hover:text-blue-600 transition-colors">Trạng thái Hệ thống</Link>
            <a href="#features" className="hover:text-blue-600 transition-colors">Tính năng 2026</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
