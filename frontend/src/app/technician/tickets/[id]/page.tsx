'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { ArrowLeft, Bot, CheckCircle2, Pin, Send, ShieldCheck, Siren, UserCheck } from 'lucide-react';
import api from '@/lib/api';
import { Ticket, TicketConversationResponse, TicketMessage } from '@/types';
import { ConfidenceBadge, EmptyState, PriorityBadge, SLABadge, Spinner, StatusBadge } from '@/components/ui';
import AISolutionViewer from '@/components/AISolutionViewer';
import EscalateModal from '@/components/EscalateModal';
import { getErrorMessage } from '@/lib/utils';
import { useAuthStore } from '@/lib/authStore';
import { useEffect, useRef, useState } from 'react';

const CLOSED = ['closed', 'resolved', 'rejected'];

export default function TechnicianTicketPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [message, setMessage] = useState('');
  const [showEscalate, setShowEscalate] = useState(false);
  const [isInternalTab, setIsInternalTab] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ticketKey = ['technician-ticket', id];

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
    queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
    queryClient.invalidateQueries({ queryKey: ['technician-all-tickets'] });
  };
  const takeover = useMutation({
    mutationFn: async () => (await api.post(`/tickets/${id}/takeover`)).data,
    onSuccess: () => { toast.success('Bạn đã tiếp nhận ticket. Các phản hồi tiếp theo sẽ do chuyên viên xử lý.'); refresh(); },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const pinMutation = useMutation({
    mutationFn: async (pinned: boolean) => (await api.post(`/tickets/${id}/pin`, { pinned })).data,
    onSuccess: (data: Ticket) => {
      toast.success(data.is_pinned ? 'Đã ghim sự cố lên đầu hàng đợi ưu tiên' : 'Đã bỏ ghim sự cố');
      refresh();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
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
      toast.success(isInternal ? 'Đã lưu ghi chú nội bộ' : 'Đã gửi phản hồi cho người dùng');
      refresh();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const close = useMutation({
    mutationFn: async () => (await api.patch(`/tickets/${id}/status`, { status: 'closed', note: 'Đóng bởi chuyên viên từ workspace.' })).data,
    onSuccess: () => { toast.success('Đã đóng ticket'); refresh(); },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  if (isLoading) return <div className="card" style={{ padding: 72, textAlign: 'center' }}><Spinner size={30} /></div>;
  if (!ticket) return <EmptyState icon="inbox" title="Không tìm thấy ticket" desc="Ticket có thể đã bị xóa hoặc bạn không có quyền truy cập." />;
  const isClosed = CLOSED.includes(ticket.status);
  const hasTakenOver = ticket.assignee_id === user?.id;
  const canReply = !isClosed && hasTakenOver;

  return <main style={{ maxWidth: 1440, margin: '0 auto' }}>
    <Link href="/technician/queue" className="btn-ghost" style={{ width: 'fit-content', textDecoration: 'none', marginBottom: 16 }}><ArrowLeft size={15} /> Quay lại hàng đợi</Link>
    <header className="card" style={{ padding: 22, marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div><div style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 800 }}>{ticket.ticket_number}</div><h1 style={{ margin: '5px 0 10px', fontSize: 25 }}>{ticket.title}</h1><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><StatusBadge status={ticket.status} />{ticket.priority && <PriorityBadge priority={ticket.priority} />}</div></div>
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
          {!ticket.assignee_id && !isClosed && <button className="btn-primary" disabled={takeover.isPending} onClick={() => takeover.mutate()}><UserCheck size={15} /> Tiếp nhận ticket</button>}
          <button className="btn-danger" disabled={isClosed} onClick={() => setShowEscalate(true)}><Siren size={15} /> Leo thang</button>
          <button className="btn-success" disabled={isClosed || close.isPending} onClick={() => close.mutate()}><CheckCircle2 size={15} /> Đóng ticket</button>
        </div>
      </div>
      <p style={{ margin: '16px 0 0', color: 'var(--text-secondary)', lineHeight: 1.65 }}>{ticket.description}</p>
    </header>
    <div className="workbench-grid">
      <section className="card tech-chat-shell">
        <header className="tech-chat-header"><div><h2>Trao đổi với người dùng</h2><p>Bạn đang thay thế AI trong cuộc hội thoại này.</p></div><span>{conversation?.items.length ?? 0} tin nhắn</span></header>
        <div className="tech-chat-thread">
          {(conversation?.items ?? []).map((item: TicketMessage) => (
            <article key={item.id} className={`tech-message tech-message--${item.sender_type}`}>
              <div className="tech-message__meta">
                {item.is_internal ? '🔒 Ghi chú nội bộ' : item.sender_type === 'technician' ? 'Bạn · Chuyên viên' : item.sender_type === 'agent' ? 'AI Agent' : item.sender_type === 'user' ? 'Người dùng' : 'Hệ thống'}
              </div>
              <div className={`tech-message__bubble ${item.is_internal ? 'message-internal-note' : ''}`}>
                {item.sender_type === 'agent' ? <AISolutionViewer content={item.content} /> : item.content}
              </div>
            </article>
          ))}
          <div ref={messagesEndRef} />
        </div>
        {canReply ? (
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
                💬 Trả lời người dùng
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
              {isInternalTab ? 'Ghi chú này CHỈ hiển thị với Kỹ thuật viên & Quản lý (Người dùng không thấy)' : 'Bạn đang phản hồi trực tiếp cho người dùng'}
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
              className="input"
              placeholder={isInternalTab ? 'Nhập ghi chú kỹ thuật nội bộ (VD: Đã kiểm tra switch cổng 4, chờ linh kiện thay thế)...' : 'Viết phản hồi gửi trực tiếp cho người dùng…'}
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
            {isClosed
              ? 'Ticket đã đóng, không thể gửi thêm tin nhắn.'
              : ticket.assignee_id
              ? 'Ticket đang do một chuyên viên khác xử lý. Bạn chỉ có thể đọc cuộc trao đổi.'
              : 'Tiếp nhận ticket để bắt đầu phản hồi người dùng.'}
          </p>
        )}
      </section>
      <aside className="card" style={{ padding: 18, alignSelf: 'start' }}>
        <h2 style={{ fontSize: 15, marginTop: 0 }}>Ngữ cảnh xử lý</h2>
        <div style={{ display: 'grid', gap: 14, fontSize: 13 }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>SLA</span>
            <div style={{ marginTop: 5 }}><SLABadge deadline={ticket.sla_deadline} /></div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Độ chắc chắn phân loại</span>
            <div style={{ marginTop: 5 }}><ConfidenceBadge score={ticket.confidence_score} /></div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Định tuyến</span>
            <div style={{ marginTop: 5, fontWeight: 700 }}>{ticket.routing_target ?? 'Chưa định tuyến'}</div>
          </div>
          {ticket.suggested_solution && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontWeight: 800, marginBottom: 10 }}>
                <Bot size={16} color="var(--blue, #2563eb)" /> Gợi ý AI
              </div>
              <AISolutionViewer content={ticket.suggested_solution} />
            </div>
          )}
        </div>
      </aside>
    </div>
    {showEscalate && <EscalateModal ticket={ticket} onClose={() => setShowEscalate(false)} onSuccess={() => refresh()} />}
  </main>;
}
