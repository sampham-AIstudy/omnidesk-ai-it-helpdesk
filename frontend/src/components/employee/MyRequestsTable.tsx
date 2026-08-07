'use client';

import { useState } from 'react';
import Link from 'next/link';
import { toast } from 'react-hot-toast';
import { CheckCircle2, MessageSquare, Star, Clock, AlertTriangle, ShieldCheck, ArrowRight } from 'lucide-react';
import { Ticket } from '@/types';

interface MyRequestsTableProps {
  tickets: Ticket[];
  onRefresh?: () => void;
}

export default function MyRequestsTable({ tickets, onRefresh }: MyRequestsTableProps) {
  const [csatModalTicket, setCsatModalTicket] = useState<Ticket | null>(null);
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState('');
  const [submittingCsat, setSubmittingCsat] = useState(false);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
      case 'classifying':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            🟡 Chờ xử lý (Open)
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            🔵 Đang xử lý (In Progress)
          </span>
        );
      case 'pending_hitl':
      case 'pending_user':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-orange-50 text-orange-700 border border-orange-200 text-xs font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
            🟠 Chờ người dùng phản hồi (Pending User)
          </span>
        );
      case 'resolved':
      case 'closed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
            <CheckCircle2 size={13} />
            🟢 Đã giải quyết (Resolved)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-bold">
            {status}
          </span>
        );
    }
  };

  const handleCsatSubmit = async () => {
    if (!csatModalTicket) return;
    setSubmittingCsat(true);
    try {
      toast.success(`Cảm ơn bạn đã đánh giá ${rating} sao cho ticket #${csatModalTicket.ticket_number}!`);
      setCsatModalTicket(null);
      setFeedback('');
      if (onRefresh) onRefresh();
    } catch {
      toast.error('Có lỗi xảy ra khi gửi đánh giá');
    } finally {
      setSubmittingCsat(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Table Container */}
      <div className="glass-card-light rounded-3xl overflow-hidden border border-slate-200 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">Mã Phiếu (#ID)</th>
                <th className="py-3.5 px-4">Tiêu Đề Sự Cố</th>
                <th className="py-3.5 px-4">Ngày Tạo</th>
                <th className="py-3.5 px-4">Trạng Thái</th>
                <th className="py-3.5 px-4 text-right">Hành Động Nhánh</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {tickets.map((t) => (
                <tr key={t.id} className="hover:bg-blue-50/40 transition-colors group">
                  <td className="py-4 px-4 font-mono font-bold text-blue-600">
                    #{t.ticket_number}
                  </td>
                  <td className="py-4 px-4 font-semibold text-slate-900 max-w-xs truncate">
                    {t.title}
                  </td>
                  <td className="py-4 px-4 text-slate-500 text-xs">
                    {new Date(t.created_at).toLocaleDateString('vi-VN')}
                  </td>
                  <td className="py-4 px-4">
                    {getStatusBadge(t.status)}
                  </td>
                  <td className="py-4 px-4 text-right space-x-2">
                    <Link
                      href={`/employee/tickets/${t.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-blue-50 hover:text-blue-600 text-slate-700 rounded-xl text-xs font-semibold transition-all"
                    >
                      <MessageSquare size={13} />
                      <span>Chi tiết</span>
                    </Link>

                    {(t.status === 'resolved' || t.status === 'in_progress') && (
                      <button
                        onClick={() => setCsatModalTicket(t)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-all"
                      >
                        <Star size={13} />
                        <span>Đóng & CSAT ⭐</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* CSAT Star Rating Modal */}
      {csatModalTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card-light rounded-3xl p-6 max-w-md w-full bg-white border border-slate-200 shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-600 mx-auto flex items-center justify-center text-xl">
                ⭐
              </div>
              <h3 className="text-lg font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Xác Nhận Đóng Phiếu & Đánh Giá CSAT
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                Phiếu #{csatModalTicket.ticket_number}: "{csatModalTicket.title}" đã được hỗ trợ xong. Hãy để lại đánh giá cho chất lượng hỗ trợ IT!
              </p>
            </div>

            {/* Star selector */}
            <div className="flex items-center justify-center gap-2 py-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setRating(star)}
                  className={`p-2 rounded-xl text-2xl transition-transform ${
                    star <= rating ? 'scale-110 text-amber-400' : 'text-slate-300 opacity-60'
                  }`}
                >
                  ★
                </button>
              ))}
            </div>

            <textarea
              placeholder="Nhận xét của bạn về mức độ hài lòng hoặc đóng góp ý kiến cho đội IT..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />

            <div className="flex items-center gap-3">
              <button
                onClick={() => setCsatModalTicket(null)}
                className="flex-1 py-2.5 bg-slate-100 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-200 transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={handleCsatSubmit}
                disabled={submittingCsat}
                className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
              >
                Xác Nhận & Đánh Giá
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
