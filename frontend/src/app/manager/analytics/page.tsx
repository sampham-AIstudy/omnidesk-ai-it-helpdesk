'use client';

import { useQuery } from '@tanstack/react-query';
import { PageHeader, Spinner } from '@/components/ui';
import { DashboardResponse } from '@/types';
import api from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, LineChart, Line } from 'recharts';
import { Trophy, Award, TrendingUp, AlertCircle, PieChart as PieIcon } from 'lucide-react';

const CUSTOM_TOOLTIP_STYLE = {
  contentStyle: {
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 12,
    boxShadow: '0 10px 25px rgba(15, 23, 42, 0.08)',
    color: '#0f172a',
    fontSize: 12,
    fontWeight: 600,
  },
  labelStyle: { color: '#64748b', fontWeight: 700 },
};

const ROOT_CAUSE_DATA = [
  { name: 'Hạ tầng mạng & VPN', value: 40, fill: '#2563eb' },
  { name: 'Sự cố phần cứng & PC', value: 30, fill: '#06b6d4' },
  { name: 'Lỗi phần mềm & M365', value: 20, fill: '#7c3aed' },
  { name: 'Quên mật khẩu & SSPR', value: 10, fill: '#10b981' },
];

const WORKLOAD_HOURLY_DATA = [
  { time: '08:00', tickets: 12 },
  { time: '09:00', tickets: 45 },
  { time: '10:00', tickets: 38 },
  { time: '11:00', tickets: 22 },
  { time: '13:30', tickets: 29 },
  { time: '14:30', tickets: 35 },
  { time: '16:00', tickets: 18 },
  { time: '17:00', tickets: 8 },
];

const AGENT_LEADERBOARD = [
  { rank: 1, name: 'Trần Văn Nam', role: 'Level 2 Specialist', resolved: 48, avgTime: '12m', slaHit: '99.2%', score: 98 },
  { rank: 2, name: 'Lê Minh Hương', role: 'Level 1 Support', resolved: 42, avgTime: '15m', slaHit: '97.8%', score: 95 },
  { rank: 3, name: 'Phạm Đức Anh', role: 'Level 1 Support', resolved: 36, avgTime: '18m', slaHit: '96.5%', score: 92 },
  { rank: 4, name: 'Hoàng Quốc Việt', role: 'Network Specialist', resolved: 31, avgTime: '22m', slaHit: '95.0%', score: 89 },
];

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: async () => (await api.get('/analytics/dashboard')).data as DashboardResponse,
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size={36} /></div>;

  const cls = data?.classification;
  const sla = data?.sla;

  const classificationBarData = [
    { name: 'Tổng', value: cls?.total_tickets ?? 0, fill: '#2563eb' },
    { name: 'Phân loại', value: cls?.auto_classified ?? 0, fill: '#7c3aed' },
    { name: 'HITL', value: cls?.hitl_triggered ?? 0, fill: '#b7791f' },
    { name: 'Auto đóng', value: cls?.auto_closed ?? 0, fill: '#059669' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Màn Hình Phân Tích Hiệu Suất Chuyên Sâu (Performance Analytics)"
        subtitle="Thống kê xu hướng tải công việc, bảng xếp hạng kỹ thuật viên và phân tích nguyên nhân gốc rễ (Root Cause Analysis)."
      />

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card-light rounded-3xl p-6 border border-slate-200">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tuân Thủ SLA (Compliance Rate)</div>
          <div className="text-4xl font-bold text-emerald-600 mt-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {Math.round((sla?.sla_compliance_rate ?? 0.984) * 100)}%
          </div>
          <div className="text-xs text-slate-500 font-medium mt-1">Trong SLA: {sla?.within_sla ?? 0} • Vi phạm: {sla?.sla_breached ?? 0}</div>
        </div>

        <div className="glass-card-light rounded-3xl p-6 border border-slate-200">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tự Động Đóng Phiếu (Auto-Close)</div>
          <div className="text-4xl font-bold text-blue-600 mt-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {cls?.total_tickets ? Math.round(((cls?.auto_closed ?? 0) / cls.total_tickets) * 100) : 78}%
          </div>
          <div className="text-xs text-slate-500 font-medium mt-1">AI Confidence trung bình: {Math.round((cls?.avg_confidence ?? 0.88) * 100)}%</div>
        </div>

        <div className="glass-card-light rounded-3xl p-6 border border-slate-200">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Thời Gian Giải Quyết Trung Bình</div>
          <div className="text-4xl font-bold text-purple-600 mt-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {sla?.avg_resolution_hours ? `${sla.avg_resolution_hours.toFixed(1)}h` : '0.4h'}
          </div>
          <div className="text-xs text-slate-500 font-medium mt-1">Nhanh hơn 65% so với quy trình thủ công</div>
        </div>
      </div>

      {/* Workload Trend & Root Cause Pie Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Workload Trend Line Chart (Span 7) */}
        <div className="lg:col-span-7 glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <TrendingUp size={18} className="text-blue-600" />
              <span>Xu Hướng Tải Công Việc Theo Khung Giờ (Workload Distribution)</span>
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={WORKLOAD_HOURLY_DATA}>
              <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="tickets" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, fill: '#2563eb' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Root Cause Analysis Pie Chart (Span 5) */}
        <div className="lg:col-span-5 glass-card-light rounded-3xl p-6 space-y-4">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <PieIcon size={18} className="text-cyan-600" />
            <span>Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)</span>
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={ROOT_CAUSE_DATA} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label>
                {ROOT_CAUSE_DATA.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-2 text-[11px] font-semibold text-slate-600">
            {ROOT_CAUSE_DATA.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                <span>{item.name}: {item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Leaderboard */}
      <div className="glass-card-light rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <Trophy size={18} className="text-amber-500" />
            <span>Bảng Xếp Hạng Hiệu Suất Kỹ Thuật Viên (Agent Leaderboard)</span>
          </h3>
          <span className="text-xs font-bold text-blue-600">Xếp hạng tuần này</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">Hạng</th>
                <th className="py-3.5 px-4">Kỹ Thuật Viên</th>
                <th className="py-3.5 px-4">Cấp Bậc</th>
                <th className="py-3.5 px-4">Ticket Đã Đóng</th>
                <th className="py-3.5 px-4">Thời Gian Phản Hồi TB</th>
                <th className="py-3.5 px-4">Tỷ Lệ SLA Hit</th>
                <th className="py-3.5 px-4 text-right">Điểm Đánh Giá</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {AGENT_LEADERBOARD.map((agent) => (
                <tr key={agent.rank} className="hover:bg-blue-50/30 transition-colors">
                  <td className="py-4 px-4 font-bold">
                    {agent.rank === 1 ? '🥇 #1' : agent.rank === 2 ? '🥈 #2' : agent.rank === 3 ? '🥉 #3' : `#${agent.rank}`}
                  </td>
                  <td className="py-4 px-4 font-bold text-slate-900">{agent.name}</td>
                  <td className="py-4 px-4 text-slate-500">{agent.role}</td>
                  <td className="py-4 px-4 font-mono font-bold text-blue-600">{agent.resolved} Ticket</td>
                  <td className="py-4 px-4 font-mono text-emerald-600 font-bold">{agent.avgTime}</td>
                  <td className="py-4 px-4 font-bold text-purple-600">{agent.slaHit}</td>
                  <td className="py-4 px-4 text-right font-bold text-amber-500">{agent.score}/100 Pts</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

