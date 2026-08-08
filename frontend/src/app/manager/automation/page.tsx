'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { GitBranch, Plus, Play, Trash2, ArrowRight, Zap, CheckCircle2 } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface AutomationRule {
  id: number;
  name: string;
  conditionField: string;
  conditionOperator: string;
  conditionValue: string;
  actionType: string;
  actionTarget: string;
  active: boolean;
}

export default function AutomationBuilderPage() {
  const [rules, setRules] = useState<AutomationRule[]>([
    {
      id: 1,
      name: 'Tự động gắn thẻ Khẩn cấp cho lỗi Sập Mạng & Server',
      conditionField: 'Title / Subject',
      conditionOperator: 'Chứa từ khóa',
      conditionValue: 'Mất mạng, Sập mạng, Crash Server',
      actionType: 'Gán nhóm xử lý & Đặt ưu tiên',
      actionTarget: 'Hạ tầng mạng • Priority Critical',
      active: true,
    },
    {
      id: 2,
      name: 'Tự động khôi phục tài khoản qua SSPR',
      conditionField: 'Category',
      conditionOperator: 'Bằng',
      conditionValue: 'Tài khoản / M365',
      actionType: 'Kích hoạt AI Auto-Resolution',
      actionTarget: 'SSPR Password Reset Agent Workflow',
      active: true,
    },
  ]);

  const [ruleName, setRuleName] = useState('');
  const [conditionValue, setConditionValue] = useState('');
  const [actionTarget, setActionTarget] = useState('Hạ tầng mạng');

  const handleAddRule = () => {
    if (!ruleName.trim() || !conditionValue.trim()) {
      toast.error('Vui lòng nhập tên quy tắc và giá trị điều kiện');
      return;
    }

    const newRule: AutomationRule = {
      id: Date.now(),
      name: ruleName.trim(),
      conditionField: 'Title / Subject',
      conditionOperator: 'Chứa từ khóa',
      conditionValue: conditionValue.trim(),
      actionType: 'Gán nhóm & Thông báo Telegram',
      actionTarget,
      active: true,
    };

    setRules((prev) => [newRule, ...prev]);
    setRuleName('');
    setConditionValue('');
    toast.success('Đã thêm quy tắc tự động hóa IF -> THEN mới!');
  };

  const toggleRule = (id: number) => {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r)));
  };

  const deleteRule = (id: number) => {
    setRules((prev) => prev.filter((r) => r.id !== id));
    toast.success('Đã xóa quy tắc');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Giao Diện Thiết Lập Tự Động Hóa (Workflow Automation Builder)"
        subtitle="Xây dựng luồng tự động định tuyến, gán kỹ thuật viên và gửi cảnh báo khẩn theo cấu hình IF (Điều kiện) -> THEN (Hành động)."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* NEW RULE BUILDER FORM (Span 5) */}
        <div className="lg:col-span-5 glass-card-light rounded-3xl p-6 space-y-5">
          <div className="flex items-center gap-2 text-blue-600 font-bold text-base pb-3 border-b border-slate-200">
            <Zap size={20} />
            <span>Tạo Quy Tắc Tự Động Hóa Mới (IF -> THEN)</span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Tên Quy Tắc Tự Động Hóa *
              </label>
              <input
                type="text"
                placeholder="Ví dụ: Cảnh báo sập hệ thống qua Telegram..."
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            {/* IF CONDITION BOX */}
            <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200 space-y-3">
              <div className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>IF (NẾU ĐIỀU KIỆN THỎA MÃN)</span>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-600 mb-1">Trường dữ liệu kiểm tra</div>
                <select className="w-full px-3 py-2 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900">
                  <option>Tiêu đề ticket (Title / Subject)</option>
                  <option>Phân loại sự cố (Category)</option>
                  <option>Cấp bậc người tạo (Is VIP / Director)</option>
                </select>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-600 mb-1">Giá trị từ khóa / Điều kiện</div>
                <input
                  type="text"
                  placeholder="Ví dụ: Mất mạng, Hỏng ổ cứng, Cháy máy..."
                  value={conditionValue}
                  onChange={(e) => setConditionValue(e.target.value)}
                  className="w-full px-3 py-2 bg-white rounded-xl border border-slate-300 text-xs font-medium text-slate-900"
                />
              </div>
            </div>

            {/* THEN ACTION BOX */}
            <div className="p-4 rounded-2xl bg-blue-50/60 border border-blue-200 space-y-3">
              <div className="text-xs font-bold text-blue-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>THEN (THỰC HIỆN HÀNH ĐỘNG)</span>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-600 mb-1">Nhóm kỹ thuật tiếp nhận</div>
                <select
                  value={actionTarget}
                  onChange={(e) => setActionTarget(e.target.value)}
                  className="w-full px-3 py-2 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900"
                >
                  <option value="Hạ tầng mạng">Hạ tầng mạng & VPN</option>
                  <option value="Phần mềm & M365">Phần mềm & Microsoft 365</option>
                  <option value="Phần cứng & Printer">Phần cứng & Máy in</option>
                  <option value="An toàn thông tin (SOC)">An toàn thông tin & Virus (SOC)</option>
                </select>
              </div>
            </div>

            <button
              type="button"
              onClick={handleAddRule}
              className="w-full py-3 shimmer-button text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 active:scale-98 transition-transform"
            >
              <Plus size={16} />
              <span>Lưu & Kích Hoạt Quy Tắc</span>
            </button>
          </div>
        </div>

        {/* ACTIVE RULES LIST (Span 7) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Danh Sách Quy Tắc Đang Kích Hoạt ({rules.filter((r) => r.active).length}/{rules.length})
            </h2>
          </div>

          <div className="space-y-3">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className={`glass-card-light rounded-2xl p-5 border transition-all ${
                  rule.active ? 'border-blue-200 bg-white' : 'border-slate-200 bg-slate-50 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-bold text-slate-900 text-sm">{rule.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleRule(rule.id)}
                      className={`px-3 py-1 rounded-full text-xs font-bold ${
                        rule.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {rule.active ? 'Đang chạy' : 'Tạm dừng'}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteRule(rule.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-amber-50 border border-amber-200/80">
                    <div className="font-bold text-amber-800 text-[11px] uppercase">NẾU (IF)</div>
                    <div className="text-slate-700 font-medium mt-0.5">
                      {rule.conditionField}: <span className="font-bold">"{rule.conditionValue}"</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-blue-50 border border-blue-200/80">
                    <div className="font-bold text-blue-800 text-[11px] uppercase">THÌ (THEN)</div>
                    <div className="text-slate-700 font-medium mt-0.5">
                      {rule.actionType} $\rightarrow$ <span className="font-bold">{rule.actionTarget}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
