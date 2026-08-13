'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import {
  ChevronRight,
  Building2,
  Building,
} from 'lucide-react';
import { MOCK_ORGANIZATIONS } from '@/lib/orgData';

export default function OrganizationTenantPage() {
  useEffect(() => {
    document.title = 'Organization & Tenant Management — Enterprise Hierarchy';
  }, []);

  return (
    <div className="enterprise-console min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white p-6 lg:p-10 relative overflow-hidden font-sans rounded-3xl">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* HEADER */}
      <header className="pt-2 pb-6 relative z-10">
        <div className="flex items-center gap-2 text-xs text-white/45 font-mono tracking-wide">
          <Link href="/admin/users" className="hover:text-white transition-colors">
            Admin
          </Link>
          <ChevronRight size={14} className="text-white/30" />
          <span className="text-white/70">Organizations</span>
        </div>

        <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl xl:text-4xl font-semibold text-white tracking-tight flex items-center gap-3">
              <Building2 className="text-cyan-400" size={32} />
              <span>Organization & Tenant Management</span>
            </h1>
            <p className="mt-2 text-sm text-white/50 leading-relaxed max-w-2xl">
              Quản lý cấu trúc Tập đoàn & Các công ty thành viên (Multi-Tenant Isolation, Cost Centers, Support Groups và Default SLA).
            </p>
          </div>
        </div>
      </header>

      {/* ENTERPRISE HIERARCHY TREE */}
      <div className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-6 sm:p-8 space-y-6 relative z-10">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-cyan-400/10 text-cyan-300 flex items-center justify-center font-bold font-mono border border-cyan-400/30">
              EG
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Enterprise Group (Tập đoàn Tổng)</h2>
              <span className="font-mono text-[10px] text-white/40">3 Companies • Multi-Tenant Isolation Active</span>
            </div>
          </div>
        </div>

        {/* Companies Grid */}
        <div className="space-y-4 pt-2">
          {MOCK_ORGANIZATIONS.map((comp) => (
            <div
              key={comp.id}
              className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4 hover:border-cyan-400/40 transition"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Building size={20} className="text-cyan-400" />
                  <h3 className="text-sm font-bold text-white">{comp.name}</h3>
                  <span className="font-mono text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/60">{comp.code}</span>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-emerald-300">{comp.defaultSla}</span>
                  <span className="text-white/40">•</span>
                  <span className="text-white/70">{comp.supportGroup}</span>
                </div>
              </div>

              {/* Departments */}
              <div className="pl-6 border-l border-white/10 space-y-2">
                <span className="font-mono text-[10px] uppercase text-white/35 block">DEPARTMENTS ({comp.departments.length})</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {comp.departments.map((d) => (
                    <div key={d.name} className="rounded-xl border border-white/5 bg-white/[0.02] p-2.5 text-xs">
                      <p className="font-medium text-white/90">{d.name}</p>
                      <p className="text-[10px] text-white/40 mt-0.5">Manager: {d.manager}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
