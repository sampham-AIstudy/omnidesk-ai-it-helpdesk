'use client';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, Spinner } from '@/components/ui';
import { ROLE_LABELS, COMPANY_LABELS, formatRelative } from '@/lib/utils';
import { User } from '@/types';
import api from '@/lib/api';

export default function UsersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => (await api.get('/admin/users')).data as User[],
  });

  const users = data ?? [];

  const ROLE_COLORS: Record<string, string> = {
    admin: '#f43f5e', manager: '#f59e0b', technician: '#06b6d4', employee: '#10b981',
  };

  return (
    <div>
      <PageHeader title="👥 Quản lý người dùng" subtitle={`${users.length} tài khoản`} />

      {isLoading ? (
        <div style={{ display:'flex', justifyContent:'center', padding:60 }}><Spinner size={36} /></div>
      ) : (
        <div className="glass-card" style={{ padding:0, overflow:'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Họ tên</th>
                <th>Username</th>
                <th>Email</th>
                <th>Vai trò</th>
                <th>Công ty</th>
                <th>Phòng ban</th>
                <th>VIP</th>
                <th>Trạng thái</th>
                <th>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td style={{ fontSize:12, color:'var(--text-muted)' }}>#{u.id}</td>
                  <td style={{ fontSize:13, fontWeight:600, color:'var(--text-primary)' }}>
                    {u.full_name}
                  </td>
                  <td style={{ fontFamily:'monospace', fontSize:12 }}>{u.username}</td>
                  <td style={{ fontSize:12, color:'var(--text-muted)' }}>{u.email}</td>
                  <td>
                    <span style={{ fontSize:11, fontWeight:700, padding:'3px 10px', borderRadius:20,
                      background:`${ROLE_COLORS[u.role]}20`, color:ROLE_COLORS[u.role],
                      border:`1px solid ${ROLE_COLORS[u.role]}40` }}>
                      {ROLE_LABELS[u.role]}
                    </span>
                  </td>
                  <td style={{ fontSize:12 }}>{COMPANY_LABELS[u.company_unit] ?? u.company_unit}</td>
                  <td style={{ fontSize:12, color:'var(--text-muted)' }}>{u.department ?? '—'}</td>
                  <td>{u.is_vip ? <span style={{ color:'#f59e0b' }}>⭐ VIP</span> : '—'}</td>
                  <td>
                    <span style={{ fontSize:11, padding:'2px 8px', borderRadius:20,
                      background: u.is_active ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)',
                      color: u.is_active ? '#10b981' : '#f43f5e',
                      border: `1px solid ${u.is_active ? 'rgba(16,185,129,0.25)' : 'rgba(244,63,94,0.25)'}` }}>
                      {u.is_active ? 'Hoạt động' : 'Vô hiệu'}
                    </span>
                  </td>
                  <td style={{ fontSize:11, color:'var(--text-muted)' }}>{formatRelative(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
