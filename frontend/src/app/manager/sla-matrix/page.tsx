'use client';

import { toast } from 'react-hot-toast';
import { Clock } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface SLARule {
  id: string;
  tier: string;
  userRank: string;
  priority: string;
  firstResponseTime: string;
  resolutionTime: string;
  escalationNotice: string;
}

const SLA_MATRIX: SLARule[] = [
    {
      id: '1',
      tier: 'Khẩn cấp (Critical / Production)',
      userRank: 'Ban Giám Đốc / VIP User',
      priority: 'Urgent',
      firstResponseTime: '5 Phút',
      resolutionTime: '1 Giờ',
      escalationNotice: 'Telegram + Email Trưởng phòng IT',
    },
    {
      id: '2',
      tier: 'Ưu tiên Cao (High Priority)',
      userRank: 'Trưởng / Phó Phòng',
      priority: 'High',
      firstResponseTime: '15 Phút',
      resolutionTime: '4 Giờ',
      escalationNotice: 'Thông báo Telegram ca trực',
    },
    {
      id: '3',
      tier: 'Tiêu chuẩn (Standard)',
      userRank: 'Nhân viên toàn công ty',
      priority: 'Medium',
      firstResponseTime: '30 Phút',
      resolutionTime: '8 Giờ',
      escalationNotice: 'Email nhắc nhở sau 4 giờ',
    },
    {
      id: '4',
      tier: 'Yêu cầu thấp (Low Request)',
      userRank: 'Tất cả nhân sự',
      priority: 'Low',
      firstResponseTime: '2 Giờ',
      resolutionTime: '24 Giờ',
      escalationNotice: 'Nhắc nhở hàng tuần',
    },
];

export default function SLAMatrixPage() {

  const handleSave = () => {
    toast.success('Đã cập nhật Ma trận Cam kết SLA!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Ma Trận Cam Kết Dịch Vụ (SLA Matrix Management)"
        subtitle="Cấu hình thời gian Phản hồi đầu tiên (First Response) và Thời gian Giải quyết hoàn toàn (Resolution Time) theo mức độ ưu tiên & cấp bậc người dùng."
      />

      <div className="glass-card-light rounded-3xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-600 font-bold text-base">
            <Clock size={20} />
            <span>Bảng Cấu Hình SLA Chuẩn Doanh Nghiệp</span>
          </div>
          <button
            onClick={handleSave}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-md transition-all"
          >
            Lưu Ma Trận SLA
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">Cấp Độ Sự Cố</th>
                <th className="py-3.5 px-4">Cấp Bậc Người Dùng</th>
                <th className="py-3.5 px-4">Ưu Tiên</th>
                <th className="py-3.5 px-4">Thời Gian Phản Hồi Đầu (First Response)</th>
                <th className="py-3.5 px-4">Thời Gian Xử Lý Xong (Resolution)</th>
                <th className="py-3.5 px-4">Kênh Cảnh Báo Leo Thang</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {SLA_MATRIX.map((row) => (
                <tr key={row.id} className="hover:bg-blue-50/30 transition-colors">
                  <td className="py-4 px-4 font-bold text-slate-900">{row.tier}</td>
                  <td className="py-4 px-4 text-slate-700">{row.userRank}</td>
                  <td className="py-4 px-4">
                    <span className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold">
                      {row.priority}
                    </span>
                  </td>
                  <td className="py-4 px-4 font-mono font-bold text-emerald-600">{row.firstResponseTime}</td>
                  <td className="py-4 px-4 font-mono font-bold text-blue-600">{row.resolutionTime}</td>
                  <td className="py-4 px-4 text-slate-600 text-xs">{row.escalationNotice}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
