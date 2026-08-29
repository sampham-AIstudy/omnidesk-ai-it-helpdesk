'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, X, Siren, ShieldAlert, Clock, CheckCheck, ExternalLink } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '@/lib/api';
import { Ticket } from '@/types';
import { formatRelative } from '@/lib/utils';

interface DynamicNotification {
  id: string;
  title: string;
  desc: string;
  time: string;
  type: 'escalated' | 'sla';
  ticketId: number;
  read: boolean;
}

export default function NotificationCenter() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [readIds, setReadIds] = useState<Set<string>>(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('read_notifications');
        return stored ? new Set(JSON.parse(stored)) : new Set();
      } catch {
        return new Set();
      }
    }
    return new Set();
  });
  const [tickets, setTickets] = useState<Ticket[]>([]);

  // Fetch real-time alerts from tickets endpoint
  useEffect(() => {
    let mounted = true;
    const fetchAlerts = async () => {
      try {
        const res = await api.get('/tickets?page=1&page_size=50');
        if (mounted && res.data?.items) {
          setTickets(res.data.items);
        }
      } catch {
        // silent catch on network hiccups
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000); // 10s auto-poll
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const notifications: DynamicNotification[] = useMemo(() => {
    const list: DynamicNotification[] = [];

    for (const t of tickets) {
      if (t.status === 'escalated' || t.sla_escalated) {
        list.push({
          id: `esc-${t.id}`,
          title: `🚨 Sự Cố Leo Thang #${t.ticket_number}`,
          desc: `${t.title} — Chuyên viên yêu cầu Quản lý can thiệp xử lý khẩn cấp.`,
          time: formatRelative(t.updated_at || t.created_at),
          type: 'escalated',
          ticketId: t.id,
          read: readIds.has(`esc-${t.id}`),
        });
      }
    }

    return list;
  }, [tickets, readIds]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    const allIds = new Set([...Array.from(readIds), ...notifications.map((n) => n.id)]);
    setReadIds(allIds);
    if (typeof window !== 'undefined') {
      localStorage.setItem('read_notifications', JSON.stringify(Array.from(allIds)));
    }
    toast.success('Đã đánh dấu đọc tất cả thông báo!');
  };

  const handleNotificationClick = (n: DynamicNotification) => {
    const nextRead = new Set(readIds);
    nextRead.add(n.id);
    setReadIds(nextRead);
    if (typeof window !== 'undefined') {
      localStorage.setItem('read_notifications', JSON.stringify(Array.from(nextRead)));
    }
    setOpen(false);

    // Get current user role from localStorage
    let role = 'technician';
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (user?.role) role = user.role;
    } catch {
      // fallback
    }

    const routePrefix = `/${role}`;
    router.push(`${routePrefix}/tickets/${n.ticketId}`);
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
        <div className="absolute right-0 sm:right-0 mt-3 w-80 sm:w-96 glass-card-light rounded-3xl p-4 shadow-2xl border border-slate-200 z-[9999] space-y-3 animate-in fade-in zoom-in-95 bg-white/95 backdrop-blur-md">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <Bell size={16} className="text-blue-600" />
              <span>Thông Báo Khẩn &amp; Leo Thang ({unreadCount})</span>
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-[11px] font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
                >
                  <CheckCheck size={12} />
                  <span>Đã đọc tất cả</span>
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-xs">
                ✨ Không có sự cố leo thang hoặc cảnh báo nào cần xử lý.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleNotificationClick(n)}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer hover:scale-[1.01] ${
                    n.read ? 'bg-slate-50/60 border-slate-100 opacity-60' : n.type === 'escalated' ? 'bg-rose-50/50 border-rose-200 shadow-xs' : 'bg-amber-50/50 border-amber-200 shadow-xs'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-bold mb-1">
                    <span className="flex items-center gap-1.5" style={{ color: n.type === 'escalated' ? '#e11d48' : '#d97706' }}>
                      {n.type === 'escalated' ? <Siren size={13} /> : <ShieldAlert size={13} />}
                      <span>{n.title}</span>
                    </span>
                    <span className="text-slate-400 font-normal text-[10px]">{n.time}</span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium leading-tight line-clamp-2">
                    {n.desc}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
