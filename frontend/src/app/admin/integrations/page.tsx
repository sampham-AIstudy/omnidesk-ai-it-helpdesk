'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { ShieldCheck, Cpu, Mail, MessageSquare, CheckCircle2, AlertCircle } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface IntegrationItem {
  id: string;
  name: string;
  category: string;
  desc: string;
  status: 'Connected' | 'Disconnected' | 'Pending Config';
  icon: string;
}

export default function AdminIntegrationsPage() {
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([
    {
      id: 'ad_sso',
      name: 'Microsoft Entra ID / Active Directory SSO',
      category: 'Xác Thực & Đồng Bộ Người Dùng',
      desc: 'Đồng bộ danh sách nhân viên toàn công ty, phòng ban và tài khoản Microsoft 365 tự động.',
      status: 'Connected',
      icon: '🔑',
    },
    {
      id: 'smtp_mail',
      name: 'SMTP Email Gateway & Exchange Server',
      category: 'Thông Báo & Gửi Thư Auto',
      desc: 'Tự động gửi email cập nhật trạng thái ticket, cảnh báo SLA quá hạn cho người dùng và IT Agent.',
      status: 'Connected',
      icon: '📧',
    },
    {
      id: 'teams_bot',
      name: 'Microsoft Teams & Zalo OA Bot Integrations',
      category: 'Kênh Trao Đổi Tức Thì',
      desc: 'Gửi tin nhắn thông báo sự cố khẩn cấp trực tiếp vào kênh Telegram/Teams của đội ngũ IT ca trực.',
      status: 'Connected',
      icon: '💬',
    },
    {
      id: 'chroma_rag',
      name: 'ChromaDB Vector Store & Mistral AI Engine',
      category: 'Trí Tuệ Nhân Tạo RAG Engine',
      desc: 'Kết nối 392+ tài liệu KB chuẩn Microsoft để phục vụ AI Agent tự động giải đáp cho End-User.',
      status: 'Connected',
      icon: '🤖',
    },
  ]);

  const handleToggleConnect = (id: string) => {
    setIntegrations((prev) =>
      prev.map((item) =>
        item.id === id
          ? { ...item, status: item.status === 'Connected' ? 'Disconnected' : 'Connected' }
          : item
      )
    );
    toast.success('Đã cập nhật trạng thái kết nối tích hợp!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Tích Hợp Hệ Thống Bên Thứ Ba (System Integrations)"
        subtitle="Dành riêng cho System Administrator: Cấu hình kết nối Active Directory/SSO, Email Gateway, Zalo/Teams Bot & AI Vector Store."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {integrations.map((item) => (
          <div key={item.id} className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-blue-50 text-2xl flex items-center justify-center border border-blue-100">
                  {item.icon}
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm" style={{ fontFamily: 'Outfit, sans-serif' }}>
                    {item.name}
                  </h3>
                  <div className="text-[11px] font-semibold text-slate-500">{item.category}</div>
                </div>
              </div>

              <span
                className={`px-3 py-1 rounded-full text-xs font-bold ${
                  item.status === 'Connected'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}
              >
                {item.status === 'Connected' ? '● Đang Tích Hợp' : '○ Tạm Dừng'}
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              {item.desc}
            </p>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => toast.success(`Mở trang cấu hình chi tiết cho ${item.name}`)}
                className="text-xs font-bold text-blue-600 hover:text-blue-700"
              >
                Cấu hình tham số API $\rightarrow$
              </button>

              <button
                onClick={() => handleToggleConnect(item.id)}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all"
              >
                {item.status === 'Connected' ? 'Tắt Tích Hợp' : 'Bật Kết Nối'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
