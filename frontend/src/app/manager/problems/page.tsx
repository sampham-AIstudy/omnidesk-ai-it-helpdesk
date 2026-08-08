'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { AlertCircle, BookOpen, Layers, Search, Plus, ShieldAlert } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface ProblemRecord {
  id: string;
  title: string;
  linkedIncidents: number;
  rootCause: string;
  workaround: string;
  status: 'Investigating' | 'Known Error (KEDB)' | 'Resolved';
}

export default function ProblemManagementPage() {
  const [problems, setProblems] = useState<ProblemRecord[]>([
    {
      id: 'PRB-001',
      title: 'Lỗi rò rỉ bộ nhớ (Memory Leak) FortiClient SSL VPN v7.2',
      linkedIncidents: 14,
      rootCause: 'Xung đột driver Virtual Adapter trên Windows 11 23H2',
      workaround: 'Thực hiện restart dịch vụ FortiSSLService hoặc cập nhật Patch v7.2.4',
      status: 'Known Error (KEDB)',
    },
    {
      id: 'PRB-002',
      title: 'Xung đột Add-in Outlook gây ngắt kết nối Exchange',
      linkedIncidents: 8,
      rootCause: 'Add-in chữ ký số hết hạn token xác thực OAuth2',
      workaround: 'Chạy Outlook ở chế độ Safe Mode (outlook.exe /safe) và xoá cache COM Add-in',
      status: 'Investigating',
    },
  ]);

  const [title, setTitle] = useState('');
  const [rootCause, setRootCause] = useState('');

  const handleCreateProblem = () => {
    if (!title.trim()) {
      toast.error('Vui lòng nhập tên Problem Record!');
      return;
    }
    const newPrb: ProblemRecord = {
      id: `PRB-00${problems.length + 1}`,
      title: title.trim(),
      linkedIncidents: 1,
      rootCause: rootCause.trim() || 'Đang phân tích nguyên nhân gốc rễ (RCA)',
      workaround: 'Đang xây dựng phương án khắc phục tạm thời (Workaround)',
      status: 'Investigating',
    };
    setProblems([newPrb, ...problems]);
    setTitle('');
    setRootCause('');
    toast.success('Đã liên kết các sự cố lặp lại thành 1 Problem Record mới!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Vấn Đề ITIL & Kho Lỗi Đã Biết (Problem Management & KEDB)"
        subtitle="Liên kết nhiều Incident lặp lại thành Problem Record, phân tích nguyên nhân gốc rễ (Root Cause Analysis) và cập nhật Kho lỗi đã biết (Known Error Database)."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Create Problem Record (Span 5) */}
        <div className="lg:col-span-5 glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-base pb-3 border-b border-slate-200" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <Layers size={18} className="text-amber-600" />
            <span>Tạo Vấn Đề Mới (Gom Nhóm Incidents)</span>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Tên Vấn Đề Cốt Lõi (Problem Title) *
              </label>
              <input
                type="text"
                placeholder="Ví dụ: Lỗi treo máy hàng loạt do Driver card màn hình..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Phân Tích Nguyên Nhân Gốc Rễ (RCA Note)
              </label>
              <textarea
                placeholder="Nhập nguyên nhân sâu xa gây sự cố diện rộng..."
                value={rootCause}
                onChange={(e) => setRootCause(e.target.value)}
                rows={3}
                className="w-full px-3.5 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-medium text-slate-900"
              />
            </div>

            <button
              onClick={handleCreateProblem}
              className="w-full py-3 shimmer-button text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2"
            >
              <Plus size={16} />
              <span>Lưu Problem Record & KEDB</span>
            </button>
          </div>
        </div>

        {/* Known Error Database (Span 7) */}
        <div className="lg:col-span-7 glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <BookOpen size={18} className="text-cyan-600" />
              <span>Kho Lỗi Đã Biết (Known Error Database - KEDB)</span>
            </h3>
          </div>

          <div className="space-y-3">
            {problems.map((prb) => (
              <div key={prb.id} className="p-4 rounded-2xl bg-white border border-slate-200 space-y-2 hover:border-blue-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-amber-600">{prb.id}</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">
                    🔗 {prb.linkedIncidents} Incidents Liên Kết
                  </span>
                </div>
                <div className="font-bold text-slate-900 text-sm">{prb.title}</div>
                <div className="p-2.5 bg-slate-50 rounded-xl text-xs space-y-1">
                  <div className="font-semibold text-slate-700">🎯 Root Cause: {prb.rootCause}</div>
                  <div className="text-blue-700">🛠️ Workaround: {prb.workaround}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
