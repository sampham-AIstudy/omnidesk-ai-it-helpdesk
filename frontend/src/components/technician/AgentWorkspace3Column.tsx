'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { 
  User, Laptop, ShieldCheck, Phone, Building, Calendar, CheckSquare, 
  Send, Lock, Mail, Search, FileText, Plus, CheckCircle2, Clock, Siren 
} from 'lucide-react';
import { Ticket } from '@/types';
import { ConfidenceBadge, PriorityBadge, SLABadge, StatusBadge } from '@/components/ui';

interface AgentWorkspace3ColumnProps {
  ticket: Ticket;
  onUpdateStatus?: (status: string) => void;
  onEscalate?: () => void;
}

export default function AgentWorkspace3Column({ ticket, onUpdateStatus, onEscalate }: AgentWorkspace3ColumnProps) {
  const [replyMode, setReplyMode] = useState<'public' | 'internal'>('public');
  const [replyText, setReplyText] = useState('');
  const [kbQuery, setKbQuery] = useState('');
  const [subtasks, setSubtasks] = useState([
    { id: 1, text: 'Sao lưu dữ liệu cá nhân & Cấu hình Outlook', done: true },
    { id: 2, text: 'Khắc phục lỗi hoặc Cài đặt lại phần mềm', done: false },
    { id: 3, text: 'Kiểm tra xác nhận với người dùng & Đóng phiếu', done: false },
  ]);
  const [newSubtask, setNewSubtask] = useState('');

  const handleInsertMacro = (macroText: string) => {
    setReplyText((prev) => (prev ? `${prev}\n${macroText}` : macroText));
    toast.success('Đã chèn mẫu phản hồi nhanh!');
  };

  const handleInsertKb = (kbTitle: string, kbSolution: string) => {
    const textToInsert = `[Hướng Dẫn Khắc Phục - ${kbTitle}]:\n${kbSolution}`;
    setReplyText((prev) => (prev ? `${prev}\n\n${textToInsert}` : textToInsert));
    toast.success('Đã chèn giải pháp KB vào khung soạn thảo!');
  };

  const toggleSubtask = (id: number) => {
    setSubtasks((prev) => prev.map((st) => (st.id === id ? { ...st, done: !st.done } : st)));
  };

  const handleAddSubtask = () => {
    if (!newSubtask.trim()) return;
    setSubtasks((prev) => [...prev, { id: Date.now(), text: newSubtask.trim(), done: false }]);
    setNewSubtask('');
  };

  const handleSendReply = () => {
    if (!replyText.trim()) return;
    toast.success(replyMode === 'public' ? 'Đã gửi phản hồi công khai cho người dùng!' : 'Đã ghi chú nội bộ cho ca trực!');
    setReplyText('');
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start text-xs sm:text-sm">

      {/* COLUMN 1: REQUESTER PROFILE & IT ASSETS (Span 3) */}
      <div className="lg:col-span-3 space-y-4">
        {/* User Identity Card */}
        <div className="glass-card-light rounded-3xl p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-blue-600 text-white font-bold flex items-center justify-center text-base shadow-md">
              {ticket.created_by_user?.full_name ? ticket.created_by_user.full_name[0] : 'U'}
            </div>
            <div>
              <div className="font-bold text-slate-900 text-sm">
                {ticket.created_by_user?.full_name || 'Người dùng IT'}
              </div>
              <div className="text-[11px] text-slate-500 font-medium">
                {ticket.created_by_user?.email || 'user@corp.example.com'}
              </div>
            </div>
          </div>

          <div className="space-y-2 pt-3 border-t border-slate-100 text-xs font-medium text-slate-600">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-400">
                <Building size={13} /> Phòng ban:
              </span>
              <span className="font-semibold text-slate-800">{ticket.created_by_user?.department || 'Phòng Kế Toán'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-400">
                <Phone size={13} /> Số nội bộ:
              </span>
              <span className="font-semibold text-slate-800">Ext: 8842</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-400">
                <ShieldCheck size={13} /> Hạng tài khoản:
              </span>
              <span className="font-bold text-blue-600">Standard Tier</span>
            </div>
          </div>
        </div>

        {/* IT Asset Widget */}
        <div className="glass-card-light rounded-3xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Laptop size={14} /> IT Asset Widget
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">Active</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 space-y-1.5">
            <div className="font-bold text-slate-900 text-xs">Dell Latitude 5420 Workstation</div>
            <div className="text-[11px] text-slate-500 font-mono">S/N: DL-99482-VN</div>
            <div className="text-[11px] text-slate-500">RAM: 16GB • SSD: 512GB • Windows 11 Enterprise</div>
          </div>

          <div className="p-3 bg-blue-50/60 rounded-2xl border border-blue-100 text-xs space-y-1">
            <div className="font-semibold text-blue-900">Bản quyền Office 365 E3</div>
            <div className="text-[11px] text-blue-700">Trạng thái: Hoạt động (Hạn 2027)</div>
          </div>
        </div>
      </div>

      {/* COLUMN 2: TIMELINE INTERACTION & REPLY PANEL (Span 6) */}
      <div className="lg:col-span-6 space-y-4">
        {/* Ticket Header Banner */}
        <div className="glass-card-light rounded-3xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono font-bold text-blue-600">#{ticket.ticket_number}</span>
            <div className="flex items-center gap-2">
              <StatusBadge status={ticket.status} />
              {ticket.priority && <PriorityBadge priority={ticket.priority} />}
            </div>
          </div>
          <h2 className="text-lg font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {ticket.title}
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed font-medium bg-slate-50 p-3 rounded-2xl border border-slate-200">
            {ticket.description}
          </p>
        </div>

        {/* Interaction Timeline Thread */}
        <div className="glass-card-light rounded-3xl p-5 space-y-4">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider pb-2 border-b border-slate-100">
            Lịch Sử Trao Đổi (Timeline Thread)
          </div>

          <div className="space-y-3">
            {/* System / AI Message */}
            <div className="p-3.5 rounded-2xl bg-blue-50/80 border border-blue-200/80 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-blue-900 flex items-center gap-1">
                  🤖 AI Agent Response (RAG Match 94%)
                </span>
                <span className="text-[11px] text-blue-600">Vừa xong</span>
              </div>
              <p className="text-xs text-blue-950 leading-relaxed font-medium">
                {ticket.suggested_solution || 'Hệ thống gợi ý kiểm tra lại đường truyền VPN FortiClient và cập nhật driver card mạng.'}
              </p>
            </div>
          </div>

          {/* Reply Box with Public / Internal Note Toggle */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
                <button
                  type="button"
                  onClick={() => setReplyMode('public')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1 ${
                    replyMode === 'public' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Mail size={13} />
                  <span>Gửi phản hồi công khai</span>
                </button>
                <button
                  type="button"
                  onClick={() => setReplyMode('internal')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1 ${
                    replyMode === 'internal' ? 'bg-amber-500 text-white shadow-xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Lock size={13} />
                  <span>Ghi chú nội bộ IT</span>
                </button>
              </div>

              {/* Quick Macros Insert */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => handleMacroInsert(handleInsertMacro, 'Cần thêm thông tin ảnh màn hình')}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-semibold"
                >
                  + Macro Ảnh Lỗi
                </button>
                <button
                  type="button"
                  onClick={() => handleMacroInsert(handleInsertMacro, 'Đã hỗ trợ reset mật khẩu qua SSPR')}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-semibold"
                >
                  + Macro SSPR
                </button>
              </div>
            </div>

            <textarea
              rows={4}
              placeholder={
                replyMode === 'public'
                  ? 'Soạn phản hồi gửi trực tiếp cho nhân viên...'
                  : 'Ghi chú ngầm chỉ các kỹ thuật viên ca trực nhìn thấy...'
              }
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              className="w-full p-3.5 bg-white rounded-2xl border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400 font-medium">
                {replyMode === 'public' ? '✉️ Email/Notification sẽ được gửi đến user' : '🔒 Đăng dưới dạng Note bảo mật'}
              </span>
              <button
                type="button"
                onClick={handleSendReply}
                className={`px-5 py-2.5 rounded-xl font-bold text-xs text-white shadow-sm flex items-center gap-1.5 transition-all ${
                  replyMode === 'public' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-amber-600 hover:bg-amber-700'
                }`}
              >
                <Send size={14} />
                <span>{replyMode === 'public' ? 'Gửi phản hồi' : 'Lưu ghi chú nội bộ'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* COLUMN 3: TICKET CONTROLS, KB SEARCH & SUBTASKS (Span 3) */}
      <div className="lg:col-span-3 space-y-4">
        {/* Ticket Metadata Controls */}
        <div className="glass-card-light rounded-3xl p-5 space-y-4">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Điều Khiển Ticket
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-[11px] font-semibold text-slate-500 mb-1">Thời hạn SLA</div>
              <SLABadge deadline={ticket.sla_deadline} />
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-500 mb-1">AI Confidence Score</div>
              <ConfidenceBadge score={ticket.confidence_score} />
            </div>

            {onUpdateStatus && (
              <div className="pt-2 border-t border-slate-100 flex items-center gap-2">
                <button
                  onClick={() => onUpdateStatus('closed')}
                  className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs flex items-center justify-center gap-1 shadow-sm"
                >
                  <CheckCircle2 size={14} />
                  <span>Xác nhận đóng</span>
                </button>
                {onEscalate && (
                  <button
                    onClick={onEscalate}
                    className="py-2 px-3 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-xl font-bold text-xs flex items-center gap-1"
                  >
                    <Siren size={14} />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* KB Search Quick Tool */}
        <div className="glass-card-light rounded-3xl p-5 space-y-3">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Search size={13} /> Knowledge Base Lookup
          </div>
          <input
            type="text"
            placeholder="Tìm tài liệu kỹ thuật..."
            value={kbQuery}
            onChange={(e) => setKbQuery(e.target.value)}
            className="w-full px-3 py-2 bg-white rounded-xl border border-slate-200 text-xs focus:ring-1 focus:ring-blue-500"
          />
          <div className="space-y-2 max-h-36 overflow-y-auto">
            <div
              onClick={() => handleInsertKb('Khắc phục Wi-Fi', 'Thực hiện reset TCP/IP stack: netsh int ip reset')}
              className="p-2 bg-slate-50 hover:bg-blue-50 rounded-xl border border-slate-200 cursor-pointer text-xs group"
            >
              <div className="font-semibold text-slate-800 group-hover:text-blue-600">Sửa lỗi Wi-Fi Windows</div>
              <div className="text-[10px] text-slate-500">Bấm để chèn hướng dẫn →</div>
            </div>
          </div>
        </div>

        {/* Sub-tasks Checklist */}
        <div className="glass-card-light rounded-3xl p-5 space-y-3">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-1"><CheckSquare size={13} /> Sub-Tasks Checklist</span>
            <span className="text-blue-600 font-bold">{subtasks.filter(s => s.done).length}/{subtasks.length}</span>
          </div>

          <div className="space-y-2">
            {subtasks.map((st) => (
              <label key={st.id} className="flex items-start gap-2 text-xs font-medium cursor-pointer text-slate-700">
                <input
                  type="checkbox"
                  checked={st.done}
                  onChange={() => toggleSubtask(st.id)}
                  className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
                />
                <span className={st.done ? 'line-through opacity-50' : ''}>{st.text}</span>
              </label>
            ))}
          </div>

          <div className="flex items-center gap-1.5 pt-2 border-t border-slate-100">
            <input
              type="text"
              placeholder="Thêm việc nhỏ..."
              value={newSubtask}
              onChange={(e) => setNewSubtask(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddSubtask()}
              className="flex-1 px-2.5 py-1.5 bg-slate-50 rounded-lg border border-slate-200 text-xs"
            />
            <button
              onClick={handleAddSubtask}
              className="p-1.5 bg-blue-600 text-white rounded-lg text-xs"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}

function handleMacroInsert(callback: (t: string) => void, text: string) {
  callback(text);
}
