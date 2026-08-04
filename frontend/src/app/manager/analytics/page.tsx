'use client';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Spinner } from '@/components/ui';
import { DashboardResponse } from '@/types';
import api from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const CUSTOM_TOOLTIP_STYLE = {
  contentStyle: {
    background: '#ffffff',
    border: '1px solid #d9dee7',
    borderRadius: 8,
    boxShadow: '0 10px 24px rgba(15, 23, 42, 0.12)',
    color: '#152033',
    fontSize: 12,
  },
  labelStyle: { color: '#526071', fontWeight: 700 },
};

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: async () => (await api.get('/analytics/dashboard')).data as DashboardResponse,
    refetchInterval: 60000,
  });

  if (isLoading) return <div style={{ display:'flex', justifyContent:'center', paddingTop:80 }}><Spinner size={36} /></div>;

  const cls = data?.classification;
  const sla = data?.sla;

  const classificationBarData = [
    { name: 'Tổng', value: cls?.total_tickets ?? 0, fill: '#2563eb' },
    { name: 'Phân loại', value: cls?.auto_classified ?? 0, fill: '#7c3aed' },
    { name: 'HITL', value: cls?.hitl_triggered ?? 0, fill: '#b7791f' },
    { name: 'Auto đóng', value: cls?.auto_closed ?? 0, fill: '#059669' },
  ];

  const slaBarData = [
    { name: 'Trong SLA', value: sla?.within_sla ?? 0, fill: '#059669' },
    { name: 'Vi phạm', value: sla?.sla_breached ?? 0, fill: '#dc2626' },
    { name: 'Leo thang', value: sla?.escalated ?? 0, fill: '#b7791f' },
  ];

  const metricCards = [
    {
      title: 'Phân loại AI', metrics: [
        { label: 'Tổng ticket', value: cls?.total_tickets ?? 0, suffix: '' },
        { label: 'Đã phân loại', value: cls?.auto_classified ?? 0, suffix: '' },
        { label: 'Confidence TB', value: Math.round((cls?.avg_confidence ?? 0) * 100), suffix: '%' },
        { label: 'Low confidence', value: Math.round((cls?.low_confidence_rate ?? 0) * 100), suffix: '%' },
        { label: 'HITL rate', value: cls?.total_tickets ? Math.round(((cls?.hitl_triggered ?? 0) / cls.total_tickets) * 100) : 0, suffix: '%' },
        { label: 'Auto-close rate', value: cls?.total_tickets ? Math.round(((cls?.auto_closed ?? 0) / cls.total_tickets) * 100) : 0, suffix: '%' },
      ]
    },
    {
      title: 'SLA Performance', metrics: [
        { label: 'SLA Compliance', value: Math.round((sla?.sla_compliance_rate ?? 0) * 100), suffix: '%' },
        { label: 'Trong SLA', value: sla?.within_sla ?? 0, suffix: '' },
        { label: 'Vi phạm SLA', value: sla?.sla_breached ?? 0, suffix: '' },
        { label: 'Leo thang', value: sla?.escalated ?? 0, suffix: '' },
        { label: 'Tổng có SLA', value: sla?.total_tickets ?? 0, suffix: '' },
        { label: 'Thời gian xử lý TB', value: sla?.avg_resolution_hours ? `${sla.avg_resolution_hours.toFixed(1)}h` : '—', suffix: '' },
      ]
    }
  ];

  return (
    <div>
      <PageHeader title="Phân tích hiệu suất" subtitle="Theo dõi chất lượng phân loại AI và mức độ tuân thủ SLA." />

      {/* Metric cards */}
      <div className="analytics-grid" style={{ marginBottom: 20 }}>
        {metricCards.map(card => (
          <div key={card.title} className="glass-card" style={{ padding:20 }}>
            <h3 className="section-title" style={{ marginBottom: 16 }}>{card.title}</h3>
            <div className="analytics-metric-grid">
              {card.metrics.map(m => (
                <div key={m.label} style={{ padding:'10px 12px', borderRadius:8, background:'var(--surface-soft)', border:'1px solid var(--border)' }}>
                  <div style={{ fontSize:10, color:'var(--text-muted)', marginBottom:4 }}>{m.label}</div>
                  <div style={{ fontSize:20, fontWeight:800, color:'var(--text)' }}>{m.value}{m.suffix}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="analytics-grid">
        <div className="glass-card" style={{ padding:20 }}>
          <h3 className="section-title" style={{ marginBottom: 16 }}>Tổng quan phân loại</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={classificationBarData} {...CUSTOM_TOOLTIP_STYLE}>
              <XAxis dataKey="name" tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
              <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
              <Bar dataKey="value" radius={[4,4,0,0]}>
                {classificationBarData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card" style={{ padding:20 }}>
          <h3 className="section-title" style={{ marginBottom: 16 }}>Trạng thái SLA</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={slaBarData} {...CUSTOM_TOOLTIP_STYLE}>
              <XAxis dataKey="name" tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
              <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
              <Bar dataKey="value" radius={[4,4,0,0]}>
                {slaBarData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Notes on eval */}
      <div style={{ marginTop:24, padding:'16px 20px', borderRadius:12,
        background:'rgba(99,102,241,0.05)', border:'1px solid rgba(99,102,241,0.15)' }}>
        <div style={{ fontSize:13, fontWeight:800, color:'var(--text)', marginBottom:6 }}>
          Về Accuracy / F1 Score
        </div>
        <div style={{ fontSize:12, color:'var(--text-secondary)', lineHeight:1.7 }}>
          Accuracy và F1 Score được tính trong <code style={{ color:'var(--violet)' }}>eval/classification_eval.py</code> với labeled ground-truth dataset.
          Chạy: <code style={{ color:'var(--cyan)' }}>python eval/classification_eval.py</code> để xem kết quả chi tiết theo từng category.
        </div>
      </div>
    </div>
  );
}
