'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/lib/authStore';

const NAV_LINKS = [
  { label: 'Giải pháp AI', href: '#features' },
  { label: 'Cơ sở tri thức (392+ KB)', href: '#knowledge' },
  { label: 'Tự phục vụ IT', href: '#self-service' },
  { label: 'Trạng thái hệ thống', href: '#status' },
];

function TechShieldIcon() {
  return (
    <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20 text-white flex-shrink-0">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    </div>
  );
}

function HamburgerIcon({ open }: { open: boolean }) {
  return (
    <div className="relative w-5 h-4 flex flex-col justify-between cursor-pointer" aria-label="Menu">
      <span
        className={`block h-[2px] bg-slate-800 origin-left rounded-full transition-transform duration-300 ${
          open ? 'rotate-45 -translate-y-0.5' : 'rotate-0'
        }`}
      />
      <span
        className={`block h-[2px] bg-slate-800 rounded-full transition-opacity duration-200 ${
          open ? 'opacity-0' : 'opacity-100'
        }`}
      />
      <span
        className={`block h-[2px] bg-slate-800 origin-left rounded-full transition-transform duration-300 ${
          open ? '-rotate-45 translate-y-0.5' : 'rotate-0'
        }`}
      />
    </div>
  );
}

export default function LandingNavbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, clearAuth } = useAuthStore();

  const getDashboardLink = () => {
    if (!user) return '/login';
    if (user.role === 'employee') return '/employee/dashboard';
    if (user.role === 'technician') return '/technician/queue';
    return '/manager/dashboard';
  };

  return (
    <>
      <nav className="fixed top-0 left-0 w-full z-50 py-4 border-b border-slate-200/80 bg-white/80 backdrop-blur-md transition-all">
        <div className="max-w-7xl mx-auto px-6 md:px-10 flex items-center justify-between">

          {/* Left: Brand Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <TechShieldIcon />
            <div className="flex flex-col">
              <span
                className="text-[20px] font-bold tracking-tight text-slate-900 leading-tight group-hover:text-blue-600 transition-colors"
                style={{ fontFamily: 'Outfit, sans-serif' }}
              >
                OmniDesk<span className="text-blue-600">.AI</span>
              </span>
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-widest -mt-0.5">
                IT Help Desk Intelligence
              </span>
            </div>
          </Link>

          {/* Center: Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-[14px] text-slate-600 hover:text-blue-600 font-semibold transition-colors duration-200 tracking-tight"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <button
                  onClick={clearAuth}
                  className="hidden md:inline-flex text-[13px] font-semibold text-slate-500 hover:text-rose-600 transition-colors duration-200 px-2 py-2"
                >
                  Đăng xuất
                </button>
                <Link
                  href={getDashboardLink()}
                  className="hidden md:inline-flex items-center justify-center px-5 py-2.5 bg-blue-600 text-white text-[13px] font-semibold rounded-xl hover:bg-blue-700 transition-all duration-200 shadow-md shadow-blue-500/25 active:scale-95"
                >
                  Vào Dashboard ({user.full_name.split(' ').slice(-1)[0]}) →
                </Link>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden md:inline-flex text-[14px] font-semibold text-slate-700 hover:text-blue-600 transition-colors duration-200 px-3 py-2"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/login"
                  className="hidden md:inline-flex items-center justify-center px-5 py-2.5 bg-blue-600 text-white text-[13px] font-semibold rounded-xl hover:bg-blue-700 transition-all duration-200 shadow-md shadow-blue-500/25 active:scale-95"
                >
                  Tạo Ticket Hỗ Trợ →
                </Link>
              </>
            )}
            <button
              className="md:hidden p-2 rounded-lg bg-slate-100 text-slate-700"
              onClick={() => setMobileOpen((p) => !p)}
              aria-label="Toggle menu"
            >
              <HamburgerIcon open={mobileOpen} />
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      <div
        className={`fixed top-0 left-0 w-full z-40 overflow-hidden bg-white/95 backdrop-blur-xl pt-24 pb-8 px-8 border-b border-slate-200 shadow-xl transition-all duration-300 ease-in-out ${
          mobileOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0 pointer-events-none'
        }`}
      >
        <div className="flex flex-col gap-4">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-3 hover:text-blue-600"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <Link
            href={getDashboardLink()}
            className="mt-2 inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white text-sm font-semibold rounded-xl shadow-md shadow-blue-500/20"
            onClick={() => setMobileOpen(false)}
          >
            {user ? 'Vào Dashboard →' : 'Đăng nhập / Tạo Ticket Hỗ Trợ →'}
          </Link>
        </div>
      </div>
    </>
  );
}


