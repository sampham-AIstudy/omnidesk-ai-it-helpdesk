'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { Bell, KeyRound, LockKeyhole, Mail, MonitorCog, Phone, Save, ShieldCheck, UserRound } from 'lucide-react';
import { toast } from 'react-hot-toast';

import { PageHeader } from '@/components/ui';
import api from '@/lib/api';
import { useAuthStore } from '@/lib/authStore';
import { getErrorMessage } from '@/lib/utils';
import type { User } from '@/types';

type ProfileSection = 'profile' | 'security' | 'preferences';

const SECTIONS: { id: ProfileSection; label: string; icon: typeof UserRound }[] = [
  { id: 'profile', label: 'Thông tin cá nhân', icon: UserRound },
  { id: 'security', label: 'Mật khẩu và truy cập', icon: ShieldCheck },
  { id: 'preferences', label: 'Tùy chọn thông báo', icon: Bell },
];

export default function EmployeeProfilePage() {
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const searchParams = useSearchParams();
  const requestedSection = searchParams.get('section');
  const [section, setSection] = useState<ProfileSection>(
    requestedSection === 'security' || requestedSection === 'preferences' ? requestedSection : 'profile'
  );
  const [emailUpdates, setEmailUpdates] = useState(true);
  const [browserUpdates, setBrowserUpdates] = useState(true);

  useEffect(() => {
    let frameId: number | undefined;
    const saved = localStorage.getItem('omni-profile-preferences');
    if (saved) {
      try {
        const preferences = JSON.parse(saved) as { emailUpdates?: boolean; browserUpdates?: boolean };
        frameId = window.requestAnimationFrame(() => {
          setEmailUpdates(preferences.emailUpdates ?? true);
          setBrowserUpdates(preferences.browserUpdates ?? true);
        });
      } catch {
        localStorage.removeItem('omni-profile-preferences');
      }
    }
    return () => { if (frameId) window.cancelAnimationFrame(frameId); };
  }, []);

  const saveProfile = useMutation({
    mutationFn: async (payload: { full_name: string; email: string; phone: string | null }) =>
      (await api.patch('/auth/me', payload)).data as User,
    onSuccess: (updatedUser) => {
      updateUser(updatedUser);
      toast.success('Đã cập nhật hồ sơ cá nhân');
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const createIdentityRequest = useMutation({
    mutationFn: async (service_name: 'Đặt lại mật khẩu' | 'Mở khóa tài khoản') =>
      (await api.post('/service-requests', {
        service_name,
        category: 'accounts',
        form_data: { username: user?.username ?? '', requested_from: 'employee_profile' },
      })).data as { request_number: string },
    onSuccess: (request) => {
      toast.success(`Đã tạo yêu cầu ${request.request_number}`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const savePreferences = () => {
    localStorage.setItem('omni-profile-preferences', JSON.stringify({ emailUpdates, browserUpdates }));
    toast.success('Đã lưu tùy chọn trên trình duyệt này');
  };

  if (!user) return null;

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <PageHeader
        title="Hồ sơ và thiết lập"
        subtitle="Quản lý thông tin cá nhân, hỗ trợ danh tính và tùy chọn thông báo của tài khoản đang đăng nhập."
      />

      <div className="grid gap-5 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav className="rounded-2xl border border-slate-200 bg-white p-2 lg:self-start" aria-label="Thiết lập hồ sơ">
          {SECTIONS.map((item) => {
            const Icon = item.icon;
            const active = section === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSection(item.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-bold transition ${active ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <Icon size={17} />{item.label}
              </button>
            );
          })}
        </nav>

        {section === 'profile' && (
          <form
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6"
            onSubmit={(event) => {
              event.preventDefault();
              const formData = new FormData(event.currentTarget);
              saveProfile.mutate({
                full_name: String(formData.get('full_name') || '').trim(),
                email: String(formData.get('email') || '').trim(),
                phone: String(formData.get('phone') || '').trim() || null,
              });
            }}
          >
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
              Tên đăng nhập, vai trò và đơn vị được quản lý bởi hệ thống danh tính nên không thể sửa tại đây.
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="space-y-2 sm:col-span-2">
                <span className="flex items-center gap-2 text-sm font-bold text-slate-800"><UserRound size={16} />Họ và tên</span>
                <input name="full_name" required minLength={2} maxLength={100} defaultValue={user.full_name} className="profile-input" />
              </label>
              <label className="space-y-2">
                <span className="flex items-center gap-2 text-sm font-bold text-slate-800"><Mail size={16} />Email</span>
                <input name="email" type="email" required defaultValue={user.email} className="profile-input" />
              </label>
              <label className="space-y-2">
                <span className="flex items-center gap-2 text-sm font-bold text-slate-800"><Phone size={16} />Số điện thoại</span>
                <input name="phone" type="tel" inputMode="tel" maxLength={30} defaultValue={user.phone || ''} placeholder="Chưa cập nhật" className="profile-input" />
              </label>
              <div className="space-y-2">
                <span className="text-sm font-bold text-slate-800">Tên đăng nhập</span>
                <div className="profile-readonly">{user.username}</div>
              </div>
              <div className="space-y-2">
                <span className="text-sm font-bold text-slate-800">Vai trò</span>
                <div className="profile-readonly">Nhân viên</div>
              </div>
            </div>
            <div className="flex justify-end border-t border-slate-200 pt-5">
              <button type="submit" disabled={saveProfile.isPending} className="btn-primary">
                <Save size={16} />{saveProfile.isPending ? 'Đang lưu' : 'Lưu thay đổi'}
              </button>
            </div>
          </form>
        )}

        {section === 'security' && (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5">
            <div>
              <h2 className="text-lg font-extrabold text-slate-900">Mật khẩu và truy cập</h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">Các yêu cầu danh tính được gửi đến Identity & Access và chỉ hoàn tất sau khi hệ thống xác minh.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <article className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                <KeyRound size={20} className="text-blue-600" />
                <h3 className="mt-4 font-bold text-slate-900">Đặt lại mật khẩu</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">Tạo yêu cầu hỗ trợ khi bạn không thể dùng kênh tự phục vụ của Entra ID.</p>
                <button type="button" onClick={() => createIdentityRequest.mutate('Đặt lại mật khẩu')} disabled={createIdentityRequest.isPending} className="btn-primary mt-4 w-full">Tạo yêu cầu</button>
              </article>
              <article className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                <LockKeyhole size={20} className="text-blue-600" />
                <h3 className="mt-4 font-bold text-slate-900">Mở khóa tài khoản</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">Gửi yêu cầu khôi phục truy cập khi tài khoản bị khóa sau nhiều lần đăng nhập sai.</p>
                <button type="button" onClick={() => createIdentityRequest.mutate('Mở khóa tài khoản')} disabled={createIdentityRequest.isPending} className="btn-primary mt-4 w-full">Tạo yêu cầu</button>
              </article>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex gap-3"><ShieldCheck size={19} className="mt-0.5 shrink-0 text-blue-600" /><p className="text-sm leading-6 text-slate-600">Cấp quyền VPN, Git, database và ứng dụng tiếp tục đi qua Service Catalog để áp dụng đúng phê duyệt.</p></div>
              <Link href="/employee/catalog/access" className="btn-ghost shrink-0">Mở Catalog</Link>
            </div>
          </section>
        )}

        {section === 'preferences' && (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5">
            <div><h2 className="text-lg font-extrabold text-slate-900">Tùy chọn thông báo</h2><p className="mt-1 text-sm text-slate-600">Các tùy chọn này được lưu riêng trên trình duyệt hiện tại.</p></div>
            <label className="profile-toggle"><span><strong>Email về ticket</strong><small>Nhận thông báo khi ticket hoặc yêu cầu dịch vụ thay đổi.</small></span><input type="checkbox" checked={emailUpdates} onChange={(event) => setEmailUpdates(event.target.checked)} /></label>
            <label className="profile-toggle"><span><strong>Thông báo trên trình duyệt</strong><small>Hiển thị nhắc việc và cập nhật khi đang mở OmniDesk.</small></span><input type="checkbox" checked={browserUpdates} onChange={(event) => setBrowserUpdates(event.target.checked)} /></label>
            <div className="flex justify-end border-t border-slate-200 pt-5"><button type="button" onClick={savePreferences} className="btn-primary"><MonitorCog size={16} />Lưu tùy chọn</button></div>
          </section>
        )}
      </div>
    </div>
  );
}
