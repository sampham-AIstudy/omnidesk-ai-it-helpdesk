'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { AlertTriangle, Siren, X, Zap } from 'lucide-react';
import api from '@/lib/api';
import { Ticket } from '@/types';
import { Spinner } from './ui';
import { getErrorMessage } from '@/lib/utils';

interface EscalateModalProps {
  ticket: Ticket;
  onClose: () => void;
  onSuccess?: () => void;
}

const REASON_OPTIONS = [
  { value: 'technical_complexity', label: 'Vượt thẩm quyền kỹ thuật / Cần quyền quản trị cấp cao (Admin/Root)' },
  { value: 'sla_risk', label: 'Nguy cơ vi phạm cam kết SLA nghiêm trọng' },
  { value: 'infrastructure_impact', label: 'Nghi vấn sự cố hạ tầng / Mạng / Server diện rộng' },
  { value: 'security_incident', label: 'Nghi vấn sự cố bảo mật & an toàn thông tin' },
  { value: 'other', label: 'Khác (Nêu rõ trong ghi chú bàn giao)' },
];

export default function EscalateModal({ ticket, onClose, onSuccess }: EscalateModalProps) {
  const queryClient = useQueryClient();
  const [reasonType, setReasonType] = useState('technical_complexity');
  const [customReason, setCustomReason] = useState('');
  const [handoverNotes, setHandoverNotes] = useState('');
  const [bumpPriority, setBumpPriority] = useState(true);

  const selectedReasonLabel = REASON_OPTIONS.find((r) => r.value === reasonType)?.label || '';
  const finalReason = reasonType === 'other' ? customReason.trim() || 'Khác' : selectedReasonLabel;

  const escalateMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/tickets/${ticket.id}/escalate`, {
          reason: finalReason,
          escalate_to: 'technician',
          bump_priority: bumpPriority,
          handover_notes: handoverNotes.trim() || null,
        })
      ).data,
    onSuccess: () => {
      toast.success('Sự cố đã được leo thang đến nhóm Kỹ thuật viên');
      queryClient.invalidateQueries({ queryKey: ['ticket', ticket.id] });
      queryClient.invalidateQueries({ queryKey: ['ticket', String(ticket.id)] });
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', String(ticket.id)] });
      queryClient.invalidateQueries({ queryKey: ['technician-tickets-queue'] });
      queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
      onSuccess?.();
      onClose();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="escalate-title">
      <div className="modal-box" style={{ maxWidth: 540 }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: 'var(--red-soft, #fef2f2)',
                color: 'var(--red, #ef4444)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <Siren size={20} />
            </div>
            <div>
              <h2 id="escalate-title" style={{ margin: 0, fontSize: 17, fontWeight: 800 }}>
                Leo thang sự cố đến Kỹ thuật viên
              </h2>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                {ticket.ticket_number} · {ticket.title}
              </span>
            </div>
          </div>
          <button className="btn-ghost" onClick={onClose} style={{ width: 32, height: 32, padding: 0 }}>
            <X size={16} />
          </button>
        </div>

        {/* Warning Callout */}
        <div
          style={{
            background: 'var(--amber-soft, #fffbeb)',
            border: '1px solid #fde68a',
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
            display: 'flex',
            gap: 10,
            fontSize: 12,
            lineHeight: 1.5,
            color: '#78350f',
          }}
        >
          <AlertTriangle size={18} color="#d97706" style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            Sự cố sẽ được chuyển sang trạng thái <strong>LEO THANG (ESCALATED)</strong> và gửi thông báo trực tiếp
            đến nhóm Kỹ thuật viên phụ trách đơn vị.
          </div>
        </div>

        {/* Form Fields */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            escalateMutation.mutate();
          }}
          style={{ display: 'grid', gap: 14 }}
        >
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6, color: 'var(--text)' }}>
              Lý do leo thang <span style={{ color: 'var(--red)' }}>*</span>
            </label>
            <select
              value={reasonType}
              onChange={(e) => setReasonType(e.target.value)}
              className="input-field"
              style={{ fontSize: 13 }}
            >
              {REASON_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {reasonType === 'other' && (
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6, color: 'var(--text)' }}>
                Nêu rõ lý do cụ thể <span style={{ color: 'var(--red)' }}>*</span>
              </label>
              <input
                type="text"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                placeholder="Nhập lý do cần leo thang..."
                className="input-field"
                required
              />
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6, color: 'var(--text)' }}>
              Ghi chú bàn giao kỹ thuật cho nhóm xử lý
            </label>
            <textarea
              rows={3}
              value={handoverNotes}
              onChange={(e) => setHandoverNotes(e.target.value)}
              placeholder="Tóm tắt các bước đã kiểm tra, phát hiện lỗi hoặc đề xuất hỗ trợ từ cấp trên..."
              className="input-field"
              style={{ resize: 'vertical' }}
            />
          </div>

          {/* Priority Bumping Option */}
          <div
            onClick={() => setBumpPriority(!bumpPriority)}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              padding: 12,
              borderRadius: 8,
              border: bumpPriority ? '1px solid #fca5a5' : '1px solid var(--border)',
              background: bumpPriority ? 'var(--red-soft, #fef2f2)' : 'var(--surface-soft)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <input
              type="checkbox"
              checked={bumpPriority}
              onChange={(e) => setBumpPriority(e.target.checked)}
              style={{ marginTop: 3, accentColor: 'var(--red, #ef4444)' }}
            />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 800, fontSize: 13, color: 'var(--red, #ef4444)' }}>
                <Zap size={14} /> Nâng mức độ ưu tiên lên KHẨN CẤP (Critical P1)
              </div>
              <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--text-secondary)' }}>
                Tự động kích hoạt còi cảnh báo đỏ trên Control Tower và rút ngắn SLA để nhóm Kỹ thuật viên xử lý ngay lập tức.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 6, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            <button type="button" className="btn-ghost" onClick={onClose} disabled={escalateMutation.isPending}>
              Hủy bỏ
            </button>
            <button
              type="submit"
              className="btn-danger"
              disabled={escalateMutation.isPending || (reasonType === 'other' && !customReason.trim())}
              style={{ minWidth: 160 }}
            >
              {escalateMutation.isPending ? <Spinner size={15} /> : <Siren size={15} />} Xác nhận leo thang
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
