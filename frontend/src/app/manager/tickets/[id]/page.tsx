'use client';

import { use, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Pin,
  Send,
  ShieldAlert,
  ShieldCheck,
  Siren,
  UserCheck,
  Wrench,
} from 'lucide-react';
import api from '@/lib/api';
import { Ticket, TicketConversationResponse, TicketMessage } from '@/types';
import {
  ConfidenceBadge,
  EmptyState,
  PageHeader,
  PriorityBadge,
  SLABadge,
  Spinner,
  StatusBadge,
} from '@/components/ui';
import AISolutionViewer from '@/components/AISolutionViewer';
import EscalateModal from '@/components/EscalateModal';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import { useAuthStore } from '@/lib/authStore';

const CLOSED = ['closed', 'resolved', 'rejected'];

export default function ManagerTicketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [message, setMessage] = useState('');
  const [hitlNote, setHitlNote] = useState('');
  const [showEscalate, setShowEscalate] = useState(false);
  const [isInternalTab, setIsInternalTab] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isApprover = user?.role === 'manager' || user?.role === 'admin';
  const ticketKey = ['manager-ticket', id];

  const { data: ticket, isLoading } = useQuery({
    queryKey: ticketKey,
    queryFn: async () => (await api.get(`/tickets/${id}`)).data as Ticket,
    enabled: Boolean(id),
    refetchInterval: 10000,
  });

  const { data: conversation } = useQuery({
    queryKey: ['ticket-messages', id],
    queryFn: async () => (await api.get(`/tickets/${id}/messages`)).data as TicketConversationResponse,
    enabled: Boolean(id),
    refetchInterval: 8000,
  });

  useEffect(() => {
    if (conversation?.items && conversation.items.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversation?.items?.length]);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ticketKey });
    queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
    queryClient.invalidateQueries({ queryKey: ['manager-tickets'] });
    queryClient.invalidateQueries({ queryKey: ['manager-dashboard'] });
  };

  const hasJoined =
    conversation?.items?.some(
      (m) =>
        m.sender_type === 'manager' ||
        (m.sender_type === 'system' && m.content.includes('QUẢN LÝ THAM GIA'))
    ) ?? false;

  const join = useMutation({
    mutationFn: async () => (await api.post(`/tickets/${id}/join`)).data,
    onSuccess: () => {
      toast.success('Bạn đã tham gia chỉ đạo cuộc trao đổi sự cố');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const send = useMutation({
    mutationFn: async (isInternal: boolean = false) =>
      (
        await api.post(`/tickets/${id}/messages`, {
          message: message.trim(),
          is_internal: isInternal,
        })
      ).data,
    onSuccess: (_, isInternal) => {
      setMessage('');
      toast.success(isInternal ? 'Đã lưu ghi chú nội bộ' : 'Đã gửi phản hồi vào thread');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const decideHitl = useMutation({
    mutationFn: async (approved: boolean) =>
      (
        await api.post(`/tickets/${id}/approve`, {
          approved,
          note: hitlNote.trim() || null,
        })
      ).data,
    onSuccess: () => {
      toast.success('Đã ghi nhận quyết định HITL');
      setHitlNote('');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const close = useMutation({
    mutationFn: async () =>
      (
        await api.patch(`/tickets/${id}/status`, {
          status: 'closed',
          note: 'Quản lý xác nhận hoàn tất và đóng sự cố.',
        })
      ).data,
    onSuccess: () => {
      toast.success('Đã đóng sự cố');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const pinMutation = useMutation({
    mutationFn: async (pinned: boolean) =>
      (
        await api.post(`/tickets/${id}/pin`, {
          pinned,
        })
      ).data,
    onSuccess: (data: Ticket) => {
      toast.success(data.is_pinned ? 'Đã ghim sự cố lên đầu hàng đợi ưu tiên' : 'Đã bỏ ghim sự cố');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const escalate = useMutation({
    mutationFn: async () => (await api.post(`/tickets/${id}/escalate`)).data,
    onSuccess: () => {
      toast.success('Đã nâng mức độ leo thang sự cố');
      refresh();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  if (isLoading)
    return (
      <div className="card" style={{ padding: 72, textAlign: 'center' }}>
        <Spinner size={30} />
      </div>
    );

  if (!ticket)
    return (
      <EmptyState
        icon="inbox"
        title="Không tìm thấy sự cố"
        desc="Sự cố có thể đã bị xoá hoặc bạn không có quyền truy cập."
      />
    );

  const isClosed = CLOSED.includes(ticket.status);

  return (
    <main style={{ maxWidth: 1440, margin: '0 auto' }}>
      <Link href="/manager/tickets" className="btn-ghost" style={{ width: 'fit-content', textDecoration: 'none', marginBottom: 16 }}>
        <ArrowLeft size={15} /> Quay lại Hàng đợi
      </Link>

      <header className="card" style={{ padding: 22, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 800 }}>{ticket.ticket_number}</div>
            <h1 style={{ margin: '5px 0 10px', fontSize: 25 }}>{ticket.title}</h1>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority ?? 'medium'} />
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                Người gửi: <strong>{ticket.created_by_user?.full_name || `Nhân viên #${ticket.submitter_id}`}</strong> ({ticket.created_by_user?.department || 'N/A'})
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'start', flexWrap: 'wrap' }}>
            <button
              className="btn-ghost"
              disabled={isClosed || pinMutation.isPending}
              onClick={() => pinMutation.mutate(!ticket.is_pinned)}
              style={{
                borderColor: ticket.is_pinned ? '#f59e0b' : undefined,
                background: ticket.is_pinned ? 'var(--amber-soft, #fffbeb)' : undefined,
                color: ticket.is_pinned ? '#92400e' : undefined,
                fontWeight: ticket.is_pinned ? 800 : undefined,
              }}
            >
              <Pin size={15} /> {ticket.is_pinned ? '📌 Bỏ ghim ưu tiên' : '📌 Ghim ưu tiên'}
            </button>
            {!hasJoined && !isClosed && (
              <button className="btn-primary" disabled={join.isPending} onClick={() => join.mutate()}>
                {join.isPending ? <Spinner size={15} /> : <UserCheck size={15} />} Tham gia chỉ đạo
              </button>
            )}
            <button className="btn-danger" disabled={isClosed} onClick={() => setShowEscalate(true)}>
              <Siren size={15} /> Leo thang
            </button>
            <button className="btn-success" disabled={isClosed || close.isPending} onClick={() => close.mutate()}>
              <CheckCircle2 size={15} /> Đóng sự cố
            </button>
          </div>
        </div>

        <p style={{ margin: '16px 0 0', color: 'var(--text-secondary)', lineHeight: 1.65 }}>{ticket.description}</p>
      </header>

      {ticket.status === 'pending_hitl' && (
        <section className="card" style={{ padding: 18, marginBottom: 16, borderColor: 'var(--amber, #f59e0b)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <ShieldCheck color="var(--amber, #f59e0b)" />
            <div>
              <strong>Quyết định HITL đang chờ phê duyệt từ Quản lý</strong>
              <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 3 }}>
                AI cần sự phê duyệt của Quản lý trước khi thực hiện hành động này.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 9, marginTop: 14, flexWrap: 'wrap' }}>
            <input
              className="input-field"
              value={hitlNote}
              onChange={(e) => setHitlNote(e.target.value)}
              placeholder="Ghi chú quyết định (không bắt buộc)…"
              style={{ flex: '1 1 280px' }}
            />
            <button className="btn-success" disabled={decideHitl.isPending} onClick={() => decideHitl.mutate(true)}>
              Phê duyệt
            </button>
            <button className="btn-danger" disabled={decideHitl.isPending} onClick={() => decideHitl.mutate(false)}>
              Từ chối
            </button>
          </div>
        </section>
      )}

      <div className="workbench-grid">
        {/* Middle Column: Chat Thread */}
        <section className="card tech-chat-shell">
          <header className="tech-chat-header">
            <div>
              <h2>Trao đổi với người dùng</h2>
              <p>
                {hasJoined
                  ? '👔 Bạn đã tham gia chỉ đạo sự cố này.'
                  : '👁️ Chế độ giám sát — Nhấn "Tham gia chỉ đạo" để gửi thông báo và hướng dẫn.'}
              </p>
            </div>
            <span>{conversation?.items.length ?? 0} tin nhắn</span>
          </header>

          <div className="tech-chat-thread">
            {(conversation?.items ?? []).map((item: TicketMessage) => (
              <article key={item.id} className={`tech-message tech-message--${item.sender_type}`}>
                <div className="tech-message__meta">
                  {item.is_internal
                    ? '🔒 Ghi chú nội bộ'
                    : item.sender_type === 'manager'
                    ? '👔 Quản lý IT'
                    : item.sender_type === 'technician'
                    ? '👨‍💻 Kỹ thuật viên'
                    : item.sender_type === 'agent'
                    ? '🤖 AI Agent'
                    : item.sender_type === 'user'
                    ? '👤 Người dùng'
                    : '📢 Hệ thống'}
                </div>
                <div className={`tech-message__bubble ${item.is_internal ? 'message-internal-note' : ''}`}>
                  {item.sender_type === 'agent' ? <AISolutionViewer content={item.content} /> : item.content}
                </div>
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {!hasJoined && !isClosed && (
            <div
              style={{
                padding: '12px 18px',
                background: 'var(--primary-soft, #eff6ff)',
                borderTop: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <div style={{ fontSize: 13, color: 'var(--text)' }}>
                👔 <strong>Bạn chưa chính thức tham gia thread này.</strong> Bấm để gửi thông báo hệ thống và bắt đầu chỉ đạo.
              </div>
              <button
                className="btn-primary"
                disabled={join.isPending}
                onClick={() => join.mutate()}
                style={{ flexShrink: 0 }}
              >
                {join.isPending ? <Spinner size={14} /> : <UserCheck size={14} />} Tham gia chỉ đạo
              </button>
            </div>
          )}

          {!isClosed ? (
            <div className="tech-chat-composer">
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <button
                  type="button"
                  onClick={() => setIsInternalTab(false)}
                  className="btn-ghost"
                  style={{
                    padding: '4px 10px',
                    fontSize: 12,
                    fontWeight: 700,
                    background: !isInternalTab ? 'var(--primary-soft, #eff6ff)' : 'transparent',
                    color: !isInternalTab ? 'var(--primary, #2563eb)' : 'var(--text-muted)',
                    borderColor: !isInternalTab ? 'var(--primary, #2563eb)' : 'transparent',
                  }}
                >
                  💬 Phản hồi công khai
                </button>
                <button
                  type="button"
                  onClick={() => setIsInternalTab(true)}
                  className="btn-ghost"
                  style={{
                    padding: '4px 10px',
                    fontSize: 12,
                    fontWeight: 700,
                    background: isInternalTab ? '#fef3c7' : 'transparent',
                    color: isInternalTab ? '#92400e' : 'var(--text-muted)',
                    borderColor: isInternalTab ? '#f59e0b' : 'transparent',
                  }}
                >
                  🔒 Ghi chú nội bộ
                </button>
              </div>
              <div className="tech-chat-presence">
                <span />
                {isInternalTab ? 'Ghi chú này CHỈ hiển thị với Kỹ thuật viên & Quản lý (Người dùng không thấy)' : 'Gửi chỉ đạo hoặc phản hồi trực tiếp cho người dùng'}
              </div>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && message.trim()) {
                    e.preventDefault();
                    send.mutate(isInternalTab);
                  }
                }}
                rows={3}
                className="input-field"
                placeholder={isInternalTab ? 'Nhập ghi chú kỹ thuật nội bộ / chỉ đạo riêng cho chuyên viên...' : 'Viết phản hồi / hướng dẫn gửi vào cuộc trao đổi…'}
              />
              <div>
                <small>Ctrl + Enter để gửi</small>
                <button
                  className={isInternalTab ? 'btn-ghost' : 'btn-primary'}
                  style={isInternalTab ? { background: '#f59e0b', color: '#fff', borderColor: '#d97706' } : undefined}
                  disabled={!message.trim() || send.isPending}
                  onClick={() => send.mutate(isInternalTab)}
                >
                  {send.isPending ? <Spinner size={15} /> : <Send size={15} />}
                  {isInternalTab ? 'Lưu ghi chú nội bộ' : 'Gửi phản hồi'}
                </button>
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '16px 18px' }}>
              Ticket đã đóng, không thể gửi thêm tin nhắn.
            </p>
          )}
        </section>

        {/* Right Column: Context */}
        <aside className="card" style={{ padding: 18, alignSelf: 'start' }}>
          <h2 style={{ fontSize: 15, marginTop: 0 }}>Ngữ cảnh xử lý</h2>
          <div style={{ display: 'grid', gap: 14, fontSize: 13, marginTop: 12 }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Thời hạn SLA</span>
              <div style={{ marginTop: 5 }}>
                <SLABadge deadline={ticket.sla_deadline} />
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Độ chắc chắn phân loại</span>
              <div style={{ marginTop: 5 }}>
                <ConfidenceBadge score={ticket.confidence_score} />
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Định tuyến xử lý</span>
              <div style={{ marginTop: 5, fontWeight: 700 }}>{ticket.routing_target ?? 'Chưa định tuyến'}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Phân loại sự cố</span>
              <div style={{ marginTop: 5, fontWeight: 700 }}>{CATEGORY_LABELS[ticket.category ?? 'other'] ?? ticket.category}</div>
            </div>
            {ticket.suggested_solution && (
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontWeight: 800, marginBottom: 10 }}>
                  <Bot size={16} color="var(--primary, #2563eb)" /> Gợi ý AI
                </div>
                <AISolutionViewer content={ticket.suggested_solution} />
              </div>
            )}
          </div>
        </aside>
      </div>
      {showEscalate && <EscalateModal ticket={ticket} onClose={() => setShowEscalate(false)} onSuccess={() => refresh()} />}
    </main>
  );
}
