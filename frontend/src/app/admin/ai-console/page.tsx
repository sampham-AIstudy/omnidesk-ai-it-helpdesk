'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Cpu, Bot, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface AgenticTaskLog {
  id: string;
  ticketId: string;
  action: string;
  status: 'Autonomous Success' | 'Flagged for Feedback';
  confidence: string;
  executionTime: string;
}

export default function AgenticAIConsolePage() {
  const [autoLevel, setAutoLevel] = useState<'copilot' | 'agentic'>('agentic');

  const [logs, setLogs] = useState<AgenticTaskLog[]>([
    {
      id: 'AI-991',
      ticketId: '#HD-9941',
      action: 'Tự động mở khóa tài khoản Entra ID SSPR & Gửi SMS OTP xác nhận',
      status: 'Autonomous Success',
      confidence: '98.5%',
      executionTime: '1.2s',
    },
    {
      id: 'AI-992',
      ticketId: '#HD-9945',
      action: 'Tự động cấp quyền truy cập Sharepoint thư mục Phòng Kế Toán',
      status: 'Autonomous Success',
      confidence: '95.0%',
      executionTime: '2.4s',
    },
  ]);

  const handleFeedback = (id: string, isGood: boolean) => {
    toast.success(isGood ? 'Đã phản hồi tích cực cho AI Agent!' : 'Đã gửi log phản hồi để Fine-Tune chống Hallucination!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trung Tâm Điều Hành AI Agentic (Agentic AI Copilot Console)"
        subtitle="Dành riêng cho System Administrator: Chuyển đổi từ 'AI trả lời gợi ý' sang 'AI Agent tự hoàn thành công việc từ đầu đến cuối', review log thực thi & Fine-Tune chống Hallucination."
      />

      {/* AI AUTOMATION MODE SWITCHER */}
      <div className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-600 font-bold text-base">
            <Cpu size={20} />
            <span>Cấu Hình Chế Độ Tự Động Hóa AI Agent (Execution Mode)</span>
          </div>
          <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Agentic Engine Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            onClick={() => { setAutoLevel('copilot'); toast.success('Đã chuyển sang chế độ AI Copilot (Chỉ gợi ý)'); }}
            className={`p-4 rounded-2xl border cursor-pointer transition-all ${
              autoLevel === 'copilot' ? 'border-blue-500 bg-blue-50/50 ring-2 ring-blue-400' : 'border-slate-200 bg-white'
            }`}
          >
            <div className="font-bold text-slate-900 text-sm">💡 Chế độ 1: AI Copilot (Gợi Ý Bàn Phím)</div>
            <div className="text-xs text-slate-500 font-medium mt-1">AI đọc KB và gợi ý giải pháp. Kỹ thuật viên phải nhấn nút xác nhận trước khi thực hiện.</div>
          </div>

          <div
            onClick={() => { setAutoLevel('agentic'); toast.success('Đã bật chế độ Agentic AI (Tự động hóa hoàn toàn)'); }}
            className={`p-4 rounded-2xl border cursor-pointer transition-all ${
              autoLevel === 'agentic' ? 'border-emerald-500 bg-emerald-50/50 ring-2 ring-emerald-400' : 'border-slate-200 bg-white'
            }`}
          >
            <div className="font-bold text-slate-900 text-sm">🤖 Chế độ 2: Agentic AI (Tự Thực Thi 100%)</div>
            <div className="text-xs text-slate-500 font-medium mt-1">AI tự đọc ý định, lấy đúng ngữ cảnh, tự kích hoạt API reset mật khẩu & cấp quyền mà không cần chờ con người.</div>
          </div>
        </div>
      </div>

      {/* AUTONOMOUS EXECUTION AUDIT LOGS */}
      <div className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
        <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
          <Bot size={18} className="text-purple-600" />
          <span>Nhật Ký AI Tự Thực Thi & Loop Phản Hồi Chống Hallucination</span>
        </h3>

        <div className="space-y-3">
          {logs.map((log) => (
            <div key={log.id} className="p-4 rounded-2xl bg-white border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-xs text-purple-600">{log.id}</span>
                  <span className="font-mono font-bold text-xs text-blue-600">{log.ticketId}</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    Confidence {log.confidence}
                  </span>
                </div>
                <div className="font-bold text-slate-900 text-xs mt-1">{log.action}</div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleFeedback(log.id, true)}
                  className="p-2 bg-slate-100 hover:bg-emerald-100 text-slate-600 hover:text-emerald-700 rounded-xl transition-all"
                >
                  <ThumbsUp size={14} />
                </button>
                <button
                  onClick={() => handleFeedback(log.id, false)}
                  className="p-2 bg-slate-100 hover:bg-rose-100 text-slate-600 hover:text-rose-700 rounded-xl transition-all"
                >
                  <ThumbsDown size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
