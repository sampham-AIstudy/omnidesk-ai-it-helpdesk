'use client';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, EmptyState, Spinner } from '@/components/ui';
import { AuditLog } from '@/types';
import { formatRelative } from '@/lib/utils';
import api from '@/lib/api';

const ACTION_ICONS: Record<string, string> = {
  ticket_created: '📋',
  ticket_classified: '🤖',
  ticket_routed: '📍',
  ticket_auto_closed: '✅',
  ticket_manually_closed: '🔒',
  ticket_escalated: '🔴',
  hitl_triggered: '⏸',
  hitl_approved: '✅',
  hitl_rejected: '❌',
  sla_warning: '⚠️',
  sla_breached: '🚨',
  comment_added: '💬',
  status_changed: '🔄',
  kb_suggestion_sent: '💡',
  runbook_executed: '⚙️',
  agent_decision: '🧠',
};

const ACTOR_COLORS: Record<string, string> = {
  agent: '#8b5cf6',
  user: '#06b6d4',
  system: '#475569',
};

export default function AuditLogPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['audit-all'],
    queryFn: async () => (await api.get('/analytics/audit-logs?page_size=100')).data,
    refetchInterval: 30000,
  });

  const logs: AuditLog[] = data?.items ?? [];

  return (
    <div>
      <PageHeader title="📜 Audit Log" subtitle="Lịch sử mọi hành động trên hệ thống" />

      <div style={{ marginBottom:24, padding:'10px 16px', borderRadius:10,
        background:'rgba(99,102,241,0.06)', border:'1px solid rgba(99,102,241,0.15)',
        fontSize:12, color:'var(--text-secondary)' }}>
        🔒 Mọi hành động từ AI Agent, người dùng và hệ thống đều được ghi nhận đầy đủ cho mục đích audit và compliance.
      </div>

      {isLoading ? (
        <div style={{ display:'flex', justifyContent:'center', padding:60 }}><Spinner size={36} /></div>
      ) : logs.length === 0 ? (
        <EmptyState icon="📭" title="Chưa có audit log" />
      ) : (
        <div className="glass-card" style={{ padding:0, overflow:'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Ticket</th>
                <th>Hành động</th>
                <th>Mô tả</th>
                <th>Thực hiện bởi</th>
                <th>Model</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td style={{ whiteSpace:'nowrap', fontSize:11 }}>{formatRelative(log.created_at)}</td>
                  <td>
                    {log.ticket_id ? (
                      <span style={{ fontSize:11, fontWeight:700, color:'var(--accent-indigo)' }}>#{log.ticket_id}</span>
                    ) : '—'}
                  </td>
                  <td>
                    <span style={{ fontSize:11, display:'flex', alignItems:'center', gap:5, whiteSpace:'nowrap' }}>
                      <span>{ACTION_ICONS[log.action] ?? '📝'}</span>
                      <span style={{ fontWeight:600 }}>{log.action.replace(/_/g,' ')}</span>
                    </span>
                  </td>
                  <td style={{ fontSize:12, maxWidth:300 }}>
                    <span style={{ display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
                      {log.description}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize:11, fontWeight:600, color:ACTOR_COLORS[log.actor_type] ?? 'var(--text-muted)' }}>
                      {log.actor_type === 'agent' ? '🤖 AI Agent' : log.actor_type === 'user' ? '👤 User' : '⚙️ System'}
                    </span>
                  </td>
                  <td style={{ fontSize:11, color:'var(--text-muted)' }}>{log.model_used ?? '—'}</td>
                  <td style={{ fontSize:12, fontWeight:600 }}>
                    {log.confidence_score !== null ? `${Math.round((log.confidence_score ?? 0) * 100)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
