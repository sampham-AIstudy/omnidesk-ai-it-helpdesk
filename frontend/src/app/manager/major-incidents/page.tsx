'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Siren, Users, Activity, MessageSquare, AlertTriangle, CheckCircle2, Radio } from 'lucide-react';
import { PageHeader } from '@/components/ui';
import { formatVietnamTime } from '@/lib/utils';

export default function MajorIncidentWarRoomPage() {
  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [timeline, setTimeline] = useState([
    { time: '21:15', author: 'Incident Commander', text: 'Phát hiện máy chủ SAP ERP sập kết nối toàn công ty. Kích hoạt War Room khẩn cấp.' },
    { time: '21:20', author: 'Lead Network Eng', text: 'Đã cô lập sự cố tại cổng Switch Core Datacenter 2. Đang chuyển luồng dự phòng.' },
  ]);

  const handleBroadcast = () => {
    if (!broadcastMsg.trim()) return;
    setTimeline([
      ...timeline,
      { time: formatVietnamTime(new Date(), { hour: '2-digit', minute: '2-digit' }), author: 'Incident Commander', text: broadcastMsg.trim() },
    ]);
    setBroadcastMsg('');
    toast.success('Đã phát thông báo khẩn cấp toàn công ty qua Email & Zalo/Teams Bot!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Phòng Điều Hành Sự Cố Nghiêm Trọng (Major Incident War Room)"
        subtitle="Màn hình dành riêng cho các sự cố sập hệ thống diện rộng: Incident Commander, timeline cập nhật thời gian thực & Phát thông báo hàng loạt."
      />

      {/* EMERGENCY BROADCAST BANNER */}
      <div className="p-6 rounded-3xl bg-rose-950 text-white border border-rose-800 shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
            <span className="font-mono font-bold text-rose-400 text-sm">MAJOR INCIDENT P1 • WAR ROOM ACTIVE</span>
          </div>
          <span className="px-3 py-1 bg-rose-900 text-rose-200 rounded-full text-xs font-bold">
            Incident Commander: Trưởng Phòng IT
          </span>
        </div>

        <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
          🚨 Sự Cố Sập Kết Nối Máy Chủ SAP ERP & Database Datacenter
        </h2>
        <p className="text-xs text-rose-200 font-medium leading-relaxed">
          Ảnh hưởng: Toàn bộ phòng Kế toán, Kho vận & Showroom không thể truy xuất dữ liệu đơn hàng. Đội ngũ IT Level 2 & Nhà cung cấp hạ tầng đang khắc phục trực tiếp.
        </p>

        {/* Broadcast Box */}
        <div className="pt-2 flex gap-3">
          <input
            type="text"
            placeholder="Soạn tin nhắn phát thông báo khẩn cấp cho toàn thể cán bộ nhân viên..."
            value={broadcastMsg}
            onChange={(e) => setBroadcastMsg(e.target.value)}
            className="flex-1 px-4 py-2.5 bg-rose-900/80 rounded-xl border border-rose-700 text-xs text-white placeholder-rose-300 focus:outline-none"
          />
          <button
            onClick={handleBroadcast}
            className="px-5 py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl shadow-lg flex items-center gap-1.5"
          >
            <Radio size={15} />
            <span>Phát Thông Báo Hàng Loạt</span>
          </button>
        </div>
      </div>

      {/* WAR ROOM TIMELINE THREAD */}
      <div className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
        <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
          <Activity size={18} className="text-rose-600" />
          <span>Nhật Ký Cập Nhật War Room (Live Operations Timeline)</span>
        </h3>

        <div className="space-y-3 font-mono text-xs">
          {timeline.map((item, idx) => (
            <div key={idx} className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3">
              <span className="font-bold text-rose-600 shrink-0">{item.time}</span>
              <div>
                <span className="font-bold text-slate-900 font-sans">{item.author}: </span>
                <span className="text-slate-700 font-sans">{item.text}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
