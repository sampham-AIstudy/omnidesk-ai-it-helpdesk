'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Building2, Hospital, KeyRound, LogIn, ShieldCheck, UserRound, Users, Wrench } from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';
import { getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

type RoleTab = 'employee' | 'technician' | 'manager' | 'admin';

interface DemoAccount {
  username: string;
  password: string;
  name: string;
  role: RoleTab;
  scope: string;
  desc: string;
}

const ACCOUNTS: Record<RoleTab, DemoAccount[]> = {
  employee: [
    { username: 'employee1', password: 'demo123', name: 'Nguyễn Văn An', role: 'employee', scope: 'BĐS X / Sales', desc: 'Gửi và theo dõi ticket cá nhân' },
    { username: 'employee_vip', password: 'demo123', name: 'Trần Thị Bích', role: 'employee', scope: 'Tập đoàn / Executive / VIP', desc: 'Ticket luôn đi qua HITL' },
    { username: 'employee_healthcare', password: 'demo123', name: 'Điều dưỡng Hoa', role: 'employee', scope: 'Y tế X / ICU', desc: 'RAG chỉ đọc tài liệu đúng quyền' },
    { username: 'employee_auto', password: 'demo123', name: 'Kinh doanh Xe', role: 'employee', scope: 'Xe X / Showroom', desc: 'Gửi ticket theo công ty thành viên' },
  ],
  technician: [
    { username: 'tech1', password: 'demo123', name: 'Lê Minh Công', role: 'technician', scope: 'Tập đoàn / IT Support', desc: 'Xử lý queue, đóng hoặc leo thang' },
  ],
  manager: [
    { username: 'manager1', password: 'demo123', name: 'Phạm Thị Dung', role: 'manager', scope: 'Tập đoàn / IT Management', desc: 'Duyệt HITL, theo dõi SLA và audit' },
  ],
  admin: [
    { username: 'admin', password: 'admin123', name: 'System Admin', role: 'admin', scope: 'Tập đoàn / IT Admin', desc: 'Quản lý người dùng và knowledge base' },
  ],
};

const ROLE_META: Record<RoleTab, { label: string; icon: React.ComponentType<{ size?: number }> }> = {
  employee: { label: 'Nhân viên', icon: UserRound },
  technician: { label: 'Kỹ thuật viên', icon: Wrench },
  manager: { label: 'Quản lý', icon: ShieldCheck },
  admin: { label: 'Admin', icon: Users },
};

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [activeTab, setActiveTab] = useState<RoleTab>('employee');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const loginMutation = useMutation({
    mutationFn: async (payload: { username: string; password: string }) => (await api.post('/auth/login', payload)).data,
    onSuccess: (data) => {
      setAuth(data.user, data.access_token);
      toast.success(`Xin chào, ${data.user.full_name}`);
      if (data.user.role === 'employee') router.push('/employee/dashboard');
      else if (data.user.role === 'technician') router.push('/technician/queue');
      else if (data.user.role === 'admin') router.push('/admin/kb');
      else router.push('/manager/dashboard');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const submitLogin = (event: React.FormEvent) => {
    event.preventDefault();
    loginMutation.mutate({ username, password });
  };

  return (
    <main className="login-shell">
      <section style={{ padding: '52px 7vw', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ maxWidth: 720 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 30, padding: '0 11px', borderRadius: 999, background: 'var(--primary-soft)', color: 'var(--primary)', fontSize: 12, fontWeight: 800, marginBottom: 18 }}>
            <KeyRound size={14} />
            Enterprise ITSM Agent Workspace
          </div>
          <h1 style={{ margin: 0, fontSize: 44, lineHeight: 1.05, fontWeight: 800, letterSpacing: 0 }}>
            Help desk vận hành bằng agent, RAG và HITL.
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 16, lineHeight: 1.7, maxWidth: 620, margin: '18px 0 28px' }}>
            Nhân viên gửi ticket, agent tự phân loại và gợi ý giải pháp. Kỹ thuật viên xử lý queue. Manager kiểm soát production, VIP, SLA và audit log.
          </p>

          <div className="login-feature-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
            {[
              { icon: Building2, title: 'Phân quyền', text: 'Theo công ty thành viên và phòng ban.' },
              { icon: Hospital, title: 'HITL bắt buộc', text: 'Production, VIP, security, low confidence.' },
              { icon: ShieldCheck, title: 'Audit', text: 'Mọi quyết định trên ticket đều lưu log.' },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="card" style={{ padding: 16 }}>
                  <Icon size={18} color="var(--primary)" />
                  <div style={{ fontWeight: 800, marginTop: 10 }}>{item.title}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.5, marginTop: 4 }}>{item.text}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)', padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ marginBottom: 18 }}>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Đăng nhập</h2>
          <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 13 }}>Chọn vai để thử đúng luồng xử lý.</p>
        </div>

        <div className="login-role-tabs" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 14 }}>
          {(Object.keys(ROLE_META) as RoleTab[]).map((role) => {
            const Icon = ROLE_META[role].icon;
            return (
              <button key={role} className={activeTab === role ? 'btn-primary' : 'btn-ghost'} style={{ height: 56, flexDirection: 'column', gap: 4, padding: 0 }} onClick={() => setActiveTab(role)}>
                <Icon size={16} />
                <span style={{ fontSize: 11 }}>{ROLE_META[role].label}</span>
              </button>
            );
          })}
        </div>

        <div style={{ display: 'grid', gap: 8, marginBottom: 18 }}>
          {ACCOUNTS[activeTab].map((account) => (
            <button
              key={account.username}
              className="card"
              style={{ padding: 12, textAlign: 'left', cursor: 'pointer' }}
              onClick={() => {
                setUsername(account.username);
                setPassword(account.password);
                loginMutation.mutate({ username: account.username, password: account.password });
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 800 }}>{account.name}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 3 }}>{account.desc}</div>
                </div>
                <span className="badge badge-in_progress">{account.scope}</span>
              </div>
            </button>
          ))}
        </div>

        <form onSubmit={submitLogin} className="card" style={{ padding: 16, display: 'grid', gap: 12, boxShadow: 'none' }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800 }}>Username</span>
            <input className="input-field" value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800 }}>Password</span>
            <input className="input-field" value={password} type="password" onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="btn-primary" disabled={loginMutation.isPending || !username || !password} style={{ height: 42 }}>
            <LogIn size={16} />
            Đăng nhập
          </button>
        </form>
      </section>
    </main>
  );
}
