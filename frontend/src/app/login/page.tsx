'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Building2, KeyRound, LogIn, ShieldCheck, UserRound, Users, Wrench, Laptop, Zap } from 'lucide-react';
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
    { username: 'employee1', password: 'demo123', name: 'Nguyễn Văn An', role: 'employee', scope: 'Phòng Kế Toán / Sales', desc: '1. End-User: Gửi ticket hỗ trợ, đọc KB, xác nhận đóng phiếu & Đánh giá 5★ CSAT' },
    { username: 'employee_vip', password: 'demo123', name: 'Trần Thị Bích', role: 'employee', scope: 'Ban Giám Đốc / VIP User', desc: '1. End-User (VIP): Ticket tự động gắn ưu tiên High & thông báo cho Trưởng phòng' },
  ],
  technician: [
    { username: 'tech1', password: 'demo123', name: 'Lê Minh Công', role: 'technician', scope: 'IT Support Level 1 & 2', desc: '2. IT Agent: Xử lý Queue, kiểm tra IT Asset Widget, viết phản hồi công khai hoặc Ghi chú nội bộ' },
  ],
  manager: [
    { username: 'manager1', password: 'demo123', name: 'Phạm Thị Dung', role: 'manager', scope: 'Trưởng Phòng IT / Team Lead', desc: '3. IT Manager: Phân bổ ticket, theo dõi Wallboard TV, cấu hình Workflow Automation & Ma trận SLA' },
  ],
  admin: [
    { username: 'admin', password: 'admin123', name: 'System Admin', role: 'admin', scope: 'Quản Trị Hệ Thống / Super Admin', desc: '4. System Admin: Quyền tối cao, Quản lý phân quyền RBAC, Kho CMDB toàn công ty & Tích hợp SSO/Bot' },
  ],
};

const ROLE_META: Record<RoleTab, { label: string; icon: React.ComponentType<{ size?: number }> }> = {
  employee: { label: '1. End-User', icon: UserRound },
  technician: { label: '2. IT Agent', icon: Wrench },
  manager: { label: '3. IT Manager', icon: ShieldCheck },
  admin: { label: '4. System Admin', icon: Users },
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
      toast.success(`Xin chào ${data.user.full_name} (${ROLE_META[data.user.role as RoleTab]?.label || data.user.role})`);
      if (data.user.role === 'employee') router.push('/employee/dashboard');
      else if (data.user.role === 'technician') router.push('/technician/queue');
      else if (data.user.role === 'admin') router.push('/admin/users');
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
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 30, padding: '0 12px', borderRadius: 999, background: 'var(--primary-soft)', color: 'var(--primary)', fontSize: 12, fontWeight: 800, marginBottom: 18 }}>
            <KeyRound size={14} />
            Enterprise IT Help Desk Architecture (4 Distinct Roles)
          </div>
          <h1 style={{ margin: 0, fontSize: 42, lineHeight: 1.1, fontWeight: 800, letterSpacing: -0.5, fontFamily: 'Outfit, sans-serif' }}>
            Hệ Thống Help Desk Phân Quyền 4 Vai Trò Chuẩn ITSM.
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 15, lineHeight: 1.7, maxWidth: 620, margin: '18px 0 28px' }}>
            Đáp ứng đầy đủ 4 nhóm vai trò doanh nghiệp: End-User (Người dùng cuối), IT Agent (Kỹ thuật viên), IT Manager (Trưởng phòng IT) và System Administrator (Super Admin).
          </p>

          <div className="login-feature-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
            {[
              { title: '1. End-User', text: 'Tạo ticket, xem bài viết KB, đóng phiếu & chấm 5★ CSAT.' },
              { title: '2. IT Agent', text: 'Nhận queue, xem IT Asset Widget, phản hồi & ghi chú nội bộ.' },
              { title: '3. IT Manager', text: 'Điều phối ticket, xem Wallboard TV, cấu hình SLA & Automation.' },
              { title: '4. System Admin', text: 'Quyền tối cao, Quản lý RBAC, Kho CMDB & Tích hợp SSO/Bot.' },
            ].map((item) => (
              <div key={item.title} className="card" style={{ padding: 14 }}>
                <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--primary)' }}>{item.title}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 11, lineHeight: 1.5, marginTop: 4 }}>{item.text}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)', padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div style={{ marginBottom: 18 }}>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: 'Outfit, sans-serif' }}>Đăng Nhập Thử Nghiệm</h2>
          <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 13 }}>Chọn vai trò bên dưới để đăng nhập trực tiếp:</p>
        </div>

        <div className="login-role-tabs" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 14 }}>
          {(Object.keys(ROLE_META) as RoleTab[]).map((role) => {
            const Icon = ROLE_META[role].icon;
            return (
              <button key={role} className={activeTab === role ? 'btn-primary' : 'btn-ghost'} style={{ height: 56, flexDirection: 'column', gap: 4, padding: 0 }} onClick={() => setActiveTab(role)}>
                <Icon size={16} />
                <span style={{ fontSize: 11, fontWeight: 700 }}>{ROLE_META[role].label}</span>
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
                <span className="badge badge-in_progress" style={{ alignSelf: 'flex-start' }}>{account.scope}</span>
              </div>
            </button>
          ))}
        </div>

        <form onSubmit={submitLogin} className="card" style={{ padding: 16, display: 'grid', gap: 12, boxShadow: 'none' }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800 }}>Tên Đăng Nhập (Username)</span>
            <input className="input-field" value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800 }}>Mật Khẩu (Password)</span>
            <input className="input-field" value={password} type="password" onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="btn-primary" disabled={loginMutation.isPending || !username || !password} style={{ height: 44, fontWeight: 800 }}>
            <LogIn size={16} />
            Đăng Nhập Ngay
          </button>
        </form>
      </section>
    </main>
  );
}

