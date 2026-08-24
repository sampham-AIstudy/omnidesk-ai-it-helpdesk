'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';

export default function LandingHero2026() {
  const { user } = useAuthStore();

  const getDashboardLink = () => {
    if (!user) return '/login';
    if (user.role === 'employee') return '/employee/dashboard';
    if (user.role === 'technician') return '/technician/queue';
    return '/manager/dashboard';
  };

  return (
    <div className="w-full px-4 sm:px-6 pt-24 pb-10">
      {/* Main Hero Container */}
      <div className="relative w-full max-w-[1400px] mx-auto rounded-[48px] bg-white border border-slate-200/50 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.03)] overflow-hidden h-[600px] flex flex-col">
        
        {/* Hero motion is part of the product's visual identity. */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden select-none">
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover scale-105 transition-transform duration-1000"
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260505_101331_74f9b798-3f00-4e86-8a01-377aa16ffeaa.mp4"
          />
        </div>

        {/* Hero Text Content */}
        <div className="relative z-20 flex-1 px-8 md:px-16 pt-12 md:pt-16 flex flex-col items-start max-w-3xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/80 backdrop-blur-md border border-slate-200/60 shadow-xs mb-6 text-xs font-semibold text-[#0a1b33]">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            <span>OmniDesk AI • Enterprise Agentic ITSM Engine</span>
          </div>

          {/* Headline */}
          <h1
            className="text-[42px] md:text-[56px] font-medium tracking-tight text-[#0a1b33] leading-[1.1] mb-5 text-left"
            style={{ fontFamily: 'Outfit, sans-serif' }}
          >
            Foundation of the<br />
            new digital IT epoch
          </h1>

          {/* Subheadline */}
          <p
            className="text-[14px] md:text-[15px] text-[#64748b] leading-relaxed max-w-xl text-left mb-8 font-normal"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            Designing intelligent AI workflows, powering 392+ KB RAG retrieval and laying the foundation of automated help desk resolution for enterprises, builders and IT teams.
          </p>

          {/* Contact Button */}
          <Link
            href="/login"
            className="px-6 py-3 bg-white text-[#0a152d] border border-slate-200/80 hover:bg-slate-50 hover:border-slate-300 font-bold rounded-full text-xs transition-all shadow-md shadow-slate-900/5 active:scale-95 flex items-center gap-2"
          >
            <span>Contact Us & Start Demo</span>
            <span className="text-blue-600 font-bold">→</span>
          </Link>
        </div>


        {/* Floating Bottom Navbar */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-30">
          <nav className="flex items-center bg-white/90 backdrop-blur-2xl px-1.5 py-1.5 rounded-full shadow-[0_12px_40px_rgba(0,0,0,0.08)] border border-slate-200/40 gap-2">
            {/* Small circular logo placeholder */}
            <div className="w-9 h-9 bg-white border border-slate-100 shadow-sm rounded-full flex items-center justify-center text-[#0a1b33] text-sm font-bold">
              ✦
            </div>

            {/* Standard Text Buttons */}
            <a
              href="#features"
              className="text-[12px] font-semibold text-slate-500 hover:text-[#0a1b33] px-3 py-1.5 transition-colors"
            >
              Products
            </a>
            <a
              href="/status"
              className="text-[12px] font-semibold text-slate-500 hover:text-[#0a1b33] px-3 py-1.5 transition-colors"
            >
              Docs & Status
            </a>

            {/* Get In Touch Button */}
            <Link
              href={getDashboardLink()}
              className="bg-white px-5 py-2 rounded-full text-[12px] font-semibold text-[#0a1b33] border border-slate-200/60 shadow-sm hover:border-slate-300 transition-all flex items-center gap-1 active:scale-95"
            >
              <span>{user ? 'Go to Workspace' : 'Get in touch'}</span>
              <ChevronRight size={14} />
            </Link>
          </nav>
        </div>
      </div>
    </div>
  );
}
