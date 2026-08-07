'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { KeyRound, ShieldCheck, CheckCircle2, Lock, ArrowRight, Bot } from 'lucide-react';
import { PageHeader, Spinner } from '@/components/ui';

export default function SelfServiceSSPRPage() {
  const [activeTab, setActiveTab] = useState<'password' | 'access'>('password');
  const [username, setUsername] = useState('nguyen.van.an');
  const [appName, setAppName] = useState('Sharepoint Kho Kế Toán');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const handleRunSSPR = () => {
    setLoading(true);
    setSuccessMsg('');
    setTimeout(() => {
      setLoading(false);
      if (activeTab === 'password') {
        setSuccessMsg(`AI Agent đã tự động tạo liên kết reset mật khẩu bảo mật gửi đến Email & SĐT của tài khoản ${username}!`);
      } else {
        setSuccessMsg(`AI Agent đã tự động kiểm tra chính sách và cấp quyền thành công cho ứng dụng ${appName}!`);
      }
      toast.success('Xử lý tự động thành công!');
    }, 1500);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cổng Tự Khôi Phục Mật Khẩu & Xin Quyền Tự Động (Self-Service SSPR & Access)"
        subtitle="Cho phép nhân viên tự đặt lại mật khẩu Entra ID hoặc tự xin quyền phần mềm tức thì mà không cần tạo ticket thủ công."
      />

      <div className="glass-card-light rounded-3xl p-6 space-y-6 max-w-2xl mx-auto border border-slate-200">
        {/* Tab Switcher */}
        <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-2xl">
          <button
            onClick={() => { setActiveTab('password'); setSuccessMsg(''); }}
            className={`flex-1 py-2.5 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'password' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600'
            }`}
          >
            <KeyRound size={15} />
            <span>Tự Reset Mật Khẩu (SSPR)</span>
          </button>
          <button
            onClick={() => { setActiveTab('access'); setSuccessMsg(''); }}
            className={`flex-1 py-2.5 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'access' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600'
            }`}
          >
            <ShieldCheck size={15} />
            <span>Tự Xin Quyền Truy Cập (Access)</span>
          </button>
        </div>

        {activeTab === 'password' ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Tên Đăng Nhập / Email Công Ty (Domain AD) *
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <p className="text-xs text-slate-500 leading-relaxed font-medium">
              💡 Mã OTP xác minh sẽ được gửi trực tiếp tới Số điện thoại di động đăng ký trong hệ thống Active Directory.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Ứng Dụng / Thư Mục Cần Cấp Quyền *
              </label>
              <select
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="w-full px-4 py-3 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="Sharepoint Kho Kế Toán">Sharepoint Thư Mục Kho Kế Toán</option>
                <option value="SAP ERP Read-Only">Tài Khoản SAP ERP Read-Only</option>
                <option value="Shared Mailbox Sales">Shared Mailbox Phòng Kinh Doanh</option>
              </select>
            </div>
          </div>
        )}

        <button
          onClick={handleRunSSPR}
          disabled={loading}
          className="w-full py-4 shimmer-button text-white font-bold text-xs rounded-2xl flex items-center justify-center gap-2"
        >
          {loading ? <Spinner size={18} /> : <Bot size={18} />}
          <span>{activeTab === 'password' ? 'Kích Hoạt AI Reset Mật Khẩu Ngay' : 'Kích Hoạt AI Cấp Quyền Tự Động'}</span>
        </button>

        {successMsg && (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2">
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
