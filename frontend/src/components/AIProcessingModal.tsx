'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Bot, CheckCircle2, Database, GitBranch, RotateCcw, ShieldAlert } from 'lucide-react';
import { Ticket } from '@/types';
import api from '@/lib/api';
import { getErrorMessage } from '@/lib/utils';
import { Spinner } from './ui';

interface Props {
  ticketId: number;
  ticketNumber: string;
  onViewTicket: () => void;
  onBackToList: () => void;
}

type StepState = 'waiting' | 'active' | 'done' | 'unavailable';

const PROCESSING_STATUSES = new Set(['open', 'classifying']);

export default function AIProcessingModal({ ticketId, ticketNumber, onViewTicket, onBackToList }: Props) {
  const [announcedSlow, setAnnouncedSlow] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setAnnouncedSlow(true), 30000);
    return () => window.clearTimeout(timer);
  }, []);

  const ticketQuery = useQuery({
    queryKey: ['ticket-processing', ticketId],
    queryFn: async () => (await api.get(`/tickets/${ticketId}`)).data as Ticket,
    refetchInterval: (query) => {
      const ticket = query.state.data;
      if (query.state.status === 'error') return 1500;
      return !ticket || PROCESSING_STATUSES.has(ticket.status) ? 1200 : false;
    },
    retry: 5,
    retryDelay: 1000,
  });

  const ticket = ticketQuery.data;
  const isProcessing = !ticket || PROCESSING_STATUSES.has(ticket.status);

  const steps = useMemo(() => {
    const hasClassification = ticket?.category != null && ticket?.confidence_score != null;
    let sourceCount = 0;
    let hasExternalGuidance = false;
    try {
      const parsedSources = JSON.parse(ticket?.rag_sources || '[]');
      sourceCount = Array.isArray(parsedSources) ? parsedSources.length : 0;
      hasExternalGuidance = Array.isArray(parsedSources) && parsedSources.some(
        (source) => typeof source === 'object' && source !== null && source.kind === 'web',
      );
    } catch {
      sourceCount = 0;
    }
    // The backend calibrates relevance by embedding backend.  A source is the
    // authoritative signal that guidance is grounded; a fixed client score
    // would incorrectly label valid hashing-embedding results as "no KB".
    const hasKbGuidance = sourceCount > 0 && !hasExternalGuidance;
    const hasResearchGuidance = sourceCount > 0 && hasExternalGuidance;
    const ragCompleted = Boolean(ticket && !isProcessing);
    const safetyCompleted = Boolean(hasClassification && !isProcessing);
    const awaitingSpecialist = ticket?.status === 'waiting_for_agent';
    const needsClarification = ticket?.status === 'needs_clarification';
    const routingCompleted = Boolean(ticket?.routing_target) || awaitingSpecialist || Boolean(ticket && !isProcessing);

    return [
      {
        title: 'Phân loại yêu cầu',
        desc: hasClassification
          ? `Đã xác định nhóm lỗi và độ tin cậy ${Math.round((ticket?.confidence_score ?? 0) * 100)}%.`
          : 'Đang đọc mô tả và xác định loại, mức ưu tiên, độ khẩn cấp.',
        icon: Bot,
        state: (hasClassification ? 'done' : 'active') as StepState,
      },
      {
        title: 'Tra cứu kho tri thức',
        desc: hasKbGuidance
          ? 'Đã tìm thấy hướng xử lý phù hợp với quyền truy cập của bạn.'
          : hasResearchGuidance
            ? 'Đã tìm thấy nguồn tham khảo công khai phù hợp; AI vẫn không thay thế quy trình nội bộ hoặc chuyên viên IT.'
          : ragCompleted
            ? 'Chưa có bài hướng dẫn đủ sát với nội dung này. AI không tự suy đoán; bạn có thể bổ sung chi tiết trong ticket.'
            : 'Chờ kết quả phân loại để tìm tài liệu liên quan.',
        icon: Database,
        state: (hasKbGuidance || hasResearchGuidance ? 'done' : ragCompleted ? 'unavailable' : hasClassification ? 'active' : 'waiting') as StepState,
      },
      {
        title: 'Kiểm tra an toàn và HITL',
        desc: ticket?.hitl_required
          ? 'Ticket cần người quản lý xác nhận trước khi tiếp tục.'
          : safetyCompleted
            ? 'Không có yêu cầu phê duyệt bổ sung ở bước này.'
            : 'Kiểm tra production, VIP, bảo mật và độ tin cậy thấp.',
        icon: ShieldAlert,
        state: (safetyCompleted ? 'done' : ragCompleted ? 'active' : 'waiting') as StepState,
      },
      {
        title: 'Định tuyến xử lý',
        desc: awaitingSpecialist && ticket?.routing_target
          ? `Đội phù hợp dự kiến: ${ticket.routing_target}. Ticket đang chờ chuyên viên tiếp nhận.`
          : awaitingSpecialist
            ? 'Ticket đang chờ chuyên viên IT tiếp nhận.'
          : needsClarification
            ? 'Cần thêm thông tin trước khi xác định đội xử lý phù hợp.'
          : ticket?.routing_target
            ? `Đội phụ trách dự kiến: ${ticket.routing_target}.`
          : routingCompleted
              ? 'Ticket đã sẵn sàng cho bước xử lý tiếp theo.'
              : 'Chờ quyết định từ quy trình xử lý.',
        icon: GitBranch,
        state: (awaitingSpecialist || (routingCompleted && !needsClarification) ? 'done' : safetyCompleted ? 'active' : 'waiting') as StepState,
      },
    ];
  }, [isProcessing, ticket]);

  return (
    <div className="modal-overlay" role="presentation">
      <section
        className="modal-box"
        style={{ maxWidth: 600 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-processing-title"
        aria-describedby="ai-processing-description"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <div style={{ width: 42, height: 42, borderRadius: 8, background: 'var(--primary-soft)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {isProcessing ? <Spinner size={21} /> : ticket?.status === 'waiting_for_agent' ? <Bot size={22} /> : <CheckCircle2 size={22} />}
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>Quy trình AI theo thời gian thực</div>
            <h2 id="ai-processing-title" style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>
              {isProcessing
                ? `Đang xử lý ${ticketNumber}`
                : ticket?.status === 'waiting_for_agent'
                  ? `${ticketNumber} đang chờ chuyên viên tiếp nhận`
                  : `${ticketNumber} đã được tiếp nhận`}
            </h2>
            <p id="ai-processing-description" className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
              Kết quả được đồng bộ trực tiếp từ hệ thống. Chỉ các bước có hướng dẫn đủ căn cứ mới được đánh dấu hoàn tất.
            </p>
          </div>
        </div>

        {ticketQuery.isError ? (
          <div className="card" style={{ padding: 16, borderColor: '#ffd4d4' }} role="alert">
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <AlertTriangle size={18} color="var(--red)" />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800, color: 'var(--red)' }}>Chưa đọc được trạng thái ticket</div>
                <div className="muted" style={{ fontSize: 12, lineHeight: 1.5, marginTop: 4 }}>
                  {getErrorMessage(ticketQuery.error)} Quy trình phía máy chủ có thể vẫn đang tiếp tục.
                </div>
                <button className="btn-ghost" style={{ marginTop: 12 }} onClick={() => ticketQuery.refetch()}>
                  <RotateCcw size={14} /> Thử lại
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }} aria-live="polite">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              const done = step.state === 'done';
              const active = step.state === 'active';
              const unavailable = step.state === 'unavailable';
              return (
                <div
                  key={`step-${idx}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: 12,
                    borderRadius: 8,
                    border: `1px solid ${active ? 'var(--primary)' : done ? '#bce7d2' : unavailable ? '#f6dd99' : 'var(--border)'}`,
                    background: active ? 'var(--primary-soft)' : done ? 'var(--green-soft)' : unavailable ? 'var(--amber-soft)' : 'var(--surface-soft)',
                  }}
                >
                  <div style={{ width: 28, height: 28, borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', color: active ? 'var(--primary)' : done ? 'var(--green)' : unavailable ? '#a16207' : 'var(--text-muted)' }}>
                    {done ? <CheckCircle2 size={18} /> : active ? <Spinner size={18} /> : unavailable ? <AlertTriangle size={18} /> : <Icon size={18} />}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 800 }}>{step.title}</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{step.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {announcedSlow && isProcessing && !ticketQuery.isError && (
          <div className="card" style={{ padding: 12, marginTop: 12, background: 'var(--amber-soft)', borderColor: '#f6dd99', fontSize: 12 }} role="status">
            Quá trình đang lâu hơn bình thường. Bạn có thể về danh sách; hệ thống vẫn tiếp tục xử lý ticket trong nền.
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', flexWrap: 'wrap', gap: 9, marginTop: 18 }}>
          <button className="btn-ghost" onClick={onBackToList}>Về danh sách</button>
          <button className="btn-primary" onClick={onViewTicket}>Xem ticket</button>
        </div>
      </section>
    </div>
  );
}
