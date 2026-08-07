'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { GitBranch, Calendar, CheckCircle2, Clock, AlertTriangle, Plus, ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface ChangeRequest {
  id: string;
  title: string;
  type: 'Standard' | 'Normal' | 'Emergency';
  requestedBy: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  scheduledDate: string;
  cabApprovalStatus: 'Approved' | 'Pending CAB Review' | 'Draft';
}

export default function ChangeManagementPage() {
  const [changes, setChanges] = useState<ChangeRequest[]>([
    {
      id: 'CR-1042',
      title: 'Nâng cấp Firmware Firewall Fortigate Core Datacenter',
      type: 'Normal',
      requestedBy: 'Lê Minh Công (IT Support)',
      riskLevel: 'Medium',
      scheduledDate: '10/08/2026 23:00',
      cabApprovalStatus: 'Approved',
    },
    {
      id: 'CR-1043',
      title: 'Vá lỗi khẩn cấp Zero-Day Windows Server 2022',
      type: 'Emergency',
      requestedBy: 'System Administrator',
      riskLevel: 'High',
      scheduledDate: '07/08/2026 01:00',
      cabApprovalStatus: 'Pending CAB Review',
    },
  ]);

  const [title, setTitle] = useState('');
  const [type, setType] = useState<'Standard' | 'Normal' | 'Emergency'>('Normal');

  const handleCreateChange = () => {
    if (!title.trim()) {
      toast.error('Vui lòng nhập tên đề xuất thay đổi!');
      return;
    }
    const newCR: ChangeRequest = {
      id: `CR-${Date.now().toString().slice(-4)}`,
      title: title.trim(),
      type,
      requestedBy: 'Trưởng nhóm Hạ tầng',
      riskLevel: type === 'Emergency' ? 'High' : 'Medium',
      scheduledDate: '12/08/2026 22:00',
      cabApprovalStatus: 'Pending CAB Review',
    };
    setChanges([newCR, ...changes]);
    setTitle('');
    toast.success('Đã tạo Change Request và gửi Hội đồng CAB duyệt!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Thay Đổi Hạ Tầng ITIL (Change Management & CAB Approval)"
        subtitle="Quy trình quản lý Change Request (Standard / Normal / Emergency), phê duyệt Hội đồng CAB và Lịch triển khai tránh xung đột (Change Calendar)."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Create Change Request Form (Span 5) */}
        <div className="lg:col-span-5 glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-base pb-3 border-b border-slate-200" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <GitBranch size={18} className="text-blue-600" />
            <span>Tạo Đề Xuất Thay Đổi (Change Request)</span>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Tiêu Đề Thay Đổi (Change Title) *
              </label>
              <input
                type="text"
                placeholder="Ví dụ: Nâng cấp RAM máy chủ Database SAP..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Phân Loại Thay Đổi (Type) *
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as any)}
                className="w-full px-3.5 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900"
              >
                <option value="Standard">Standard (Thay đổi tiêu chuẩn theo quy trình)</option>
                <option value="Normal">Normal (Thay đổi bình thường cần CAB duyệt)</option>
                <option value="Emergency">Emergency (Thay đổi khẩn cấp xử lý sự cố)</option>
              </select>
            </div>

            <button
              onClick={handleCreateChange}
              className="w-full py-3 shimmer-button text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2"
            >
              <Plus size={16} />
              <span>Gửi Đề Xuất Cho Hội Đồng CAB</span>
            </button>
          </div>
        </div>

        {/* Change Calendar & Approvals (Span 7) */}
        <div className="lg:col-span-7 glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <Calendar size={18} className="text-purple-600" />
              <span>Lịch Triển Khai & Duyệt CAB (Change Advisory Board)</span>
            </h3>
          </div>

          <div className="space-y-3">
            {changes.map((cr) => (
              <div key={cr.id} className="p-4 rounded-2xl bg-white border border-slate-200 space-y-2 hover:border-blue-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-blue-600">{cr.id}</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                    cr.type === 'Emergency' ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {cr.type}
                  </span>
                </div>
                <div className="font-bold text-slate-900 text-sm">{cr.title}</div>
                <div className="flex items-center justify-between text-xs text-slate-500 font-medium pt-2 border-t border-slate-100">
                  <span>👤 {cr.requestedBy}</span>
                  <span>📅 {cr.scheduledDate}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
