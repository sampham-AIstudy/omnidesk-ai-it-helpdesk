'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, ShieldCheck, Activity } from 'lucide-react';

interface ServiceStatus {
  name: string;
  category: string;
  status: 'Operational' | 'Degraded' | 'Outage';
  uptime: string;
  latency: string;
}

export default function PublicStatusPage() {
  const [services] = useState<ServiceStatus[]>([
    { name: 'Microsoft 365 & Exchange Email', category: 'Email & Communication', status: 'Operational', uptime: '99.99%', latency: '12ms' },
    { name: 'FortiClient SSL VPN Gateway', category: 'Network & Remote Access', status: 'Operational', uptime: '99.95%', latency: '24ms' },
    { name: 'SAP ERP & Financial Core', category: 'Enterprise Software', status: 'Operational', uptime: '99.90%', latency: '35ms' },
    { name: 'Microsoft Entra ID / Active Directory', category: 'Identity & Access Management', status: 'Operational', uptime: '100%', latency: '8ms' },
    { name: 'Datacenter Primary SAN Storage', category: 'Infrastructure & Storage', status: 'Operational', uptime: '99.99%', latency: '4ms' },
  ]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-blue-600 selection:text-white p-6 md:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">
              <Activity size={16} /> OmniDesk AI • Public Status Center
            </div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Trạng Thái Hoạt Động Hệ Thống CNTT (System Operational Status)
            </h1>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all self-start sm:self-auto"
          >
            ← Về Trang Chủ
          </Link>
        </div>

        {/* System All Operational Banner */}
        <div className="p-6 rounded-3xl bg-emerald-500 text-white shadow-xl shadow-emerald-500/10 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center text-2xl font-bold">
              ✓
            </div>
            <div>
              <div className="text-lg font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Tất Cả Dịch Vụ Đang Hoạt Động Mượt Mà (All Systems Operational)
              </div>
              <div className="text-xs text-emerald-100 font-medium">
                Cập nhật lúc {new Date().toLocaleTimeString('vi-VN')} • Không ghi nhận sự cố gián đoạn
              </div>
            </div>
          </div>
        </div>

        {/* Services List */}
        <div className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
          <h2 className="font-bold text-slate-900 text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Chi Tiết Dịch Vụ Hạ Tầng Doanh Nghiệp
          </h2>

          <div className="space-y-3">
            {services.map((s) => (
              <div key={s.name} className="p-4 rounded-2xl bg-white border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-blue-300 transition-all">
                <div>
                  <div className="font-bold text-slate-900 text-sm">{s.name}</div>
                  <div className="text-xs text-slate-500 font-medium">{s.category}</div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right text-xs">
                    <div className="font-mono font-bold text-slate-700">Uptime {s.uptime}</div>
                    <div className="text-[11px] text-slate-400 font-medium">Độ trễ: {s.latency}</div>
                  </div>

                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Operational
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
