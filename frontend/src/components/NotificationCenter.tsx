'use client';

import { useState } from 'react';
import { Bell, X, Check, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface AppNotification {
  id: string;
  title: string;
  desc: string;
  time: string;
  read: boolean;
  type: 'sla' | 'approval' | 'system';
}

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([
    {
      id: 'n1',
      title: 'Cảnh báo SLA Sắp Vi Phạm',
      desc: 'Ticket #HD-9941 còn 15 phút là đến deadline SLA First Response.',
      time: '5 phút trước',
      read: false,
      type: 'sla',
    },
    {
      id: 'n2',
      title: 'Yêu Cầu Duyệt Change CAB',
      desc: 'Change Request #CR-1043 đang chờ bạn bỏ phiếu phê duyệt.',
      time: '20 phút trước',
      read: false,
      type: 'approval',
    },
    {
      id: 'n3',
      title: 'Xác Nhận Đóng Phiếu Hỗ Trợ',
      desc: 'Người dùng Nguyễn Văn An đã đánh giá 5★ CSAT cho ticket #HD-9912.',
      time: '1 giờ trước',
      read: true,
      type: 'system',
    },
  ]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    toast.success('Đã đánh dấu đọc tất cả thông báo!');
  };

  return (
    <div className="relative inline-block">
      {/* Bell Icon Trigger */}
      <button
        onClick={() => setOpen((p) => !p)}
        className="relative p-2.5 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-all cursor-pointer"
        aria-label="Trung tâm thông báo"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-600 text-white font-bold text-[10px] flex items-center justify-center animate-bounce shadow-md">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Notification Drawer Dropdown */}
      {open && (
        <div className="absolute left-0 sm:left-0 mt-3 w-80 sm:w-96 glass-card-light rounded-3xl p-4 shadow-2xl border border-slate-200 z-[9999] space-y-3 animate-in fade-in zoom-in-95 bg-white/95 backdrop-blur-md">

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <Bell size={16} className="text-blue-600" />
              <span>Thông Báo In-App ({unreadCount})</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={markAllAsRead}
                className="text-[11px] font-bold text-blue-600 hover:text-blue-700"
              >
                Đã đọc tất cả
              </button>
              <button
                onClick={() => setOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-80 overflow-y-auto">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`p-3 rounded-2xl border transition-all ${
                  n.read ? 'bg-slate-50/60 border-slate-100 opacity-70' : 'bg-white border-blue-200 shadow-2xs'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] font-bold mb-1">
                  <span className={n.type === 'sla' ? 'text-rose-600' : n.type === 'approval' ? 'text-amber-600' : 'text-blue-600'}>
                    {n.title}
                  </span>
                  <span className="text-slate-400 font-normal">{n.time}</span>
                </div>
                <p className="text-xs text-slate-600 font-medium leading-tight">
                  {n.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
