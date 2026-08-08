'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock,
  Database,
  History,
  MessageCircle,
  RotateCcw,
  Send,
  ShieldCheck,
  Star,
  UserCheck,
  UserPlus,
  X,
} from 'lucide-react';

import {
  ConfidenceBadge,
  EmptyState,
  HITLBadge,
  PriorityBadge,
  Spinner,
  StatusBadge,
} from '@/components/ui';
import { Ticket, TicketConversationResponse, TicketMessage } from '@/types';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import { useAuthStore } from '@/lib/authStore';
import api from '@/lib/api';

// Real-time Dynamic SLA Countdown Component
function DynamicSLACountdown({ deadline, isEscalated }: { deadline: string | null; isEscalated: boolean }) {
  const [timeLeft, setTimeLeft] = useState<string>('');
  const [slaStatus, setSlaStatus] = useState<'on_track' | 'at_risk' | 'breached'>('on_track');

  useEffect(() => {
    if (!deadline) {
      setTimeLeft('Chưa thiết lập SLA');
      return;
    }

    const calculate = () => {
      const target = new Date(deadline).getTime();
      const now = new Date().getTime();
      const diff = target - now;

      if (diff <= 0 || isEscalated) {
        setSlaStatus('breached');
        const absDiff = Math.abs(diff);
        const hours = Math.floor(absDiff / (1000 * 60 * 60));
        const mins = Math.floor((absDiff % (1000 * 60 * 60)) / (1000 * 60));
        setTimeLeft(`SLA vi phạm ${hours > 0 ? `${hours}h ` : ''}${mins}m`);
      } else {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        if (hours < 1) {
          setSlaStatus('at_risk');
        } else {
          setSlaStatus('on_track');
        }
        setTimeLeft(`SLA còn ${hours > 0 ? `${hours}h ` : ''}${mins}m`);
      }
    };

    calculate();
    const timer = setInterval(calculate, 10000);
    return () => clearInterval(timer);
  }, [deadline, isEscalated]);

  const badgeStyle =
    slaStatus === 'breached'
      ? 'bg-rose-100 text-rose-700 border-rose-200'
      : slaStatus === 'at_risk'
        ? 'bg-amber-100 text-amber-800 border-amber-200'
        : 'bg-emerald-100 text-emerald-800 border-emerald-200';

  return (
    <div className="flex items-center gap-2">
      <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${badgeStyle}`}>
        {timeLeft}
      </span>
      <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
        {slaStatus === 'breached' ? 'Breached' : slaStatus === 'at_risk' ? 'At Risk' : 'On Track'}
      </span>
    </div>
  );
}

export default function RiotStyleTicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [message, setMessage] = useState('');
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reopenReason, setReopenReason] = useState('');
  const [selectedRating, setSelectedRating] = useState<number>(0);
  const [ratingFeedback, setRatingFeedback] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [optimisticMessages, setOptimisticMessages] = useState<TicketMessage[]>([]);
  const [lightboxImage, setLightboxImage] = useState<{ name: string; url: string } | null>(null);

  // 1. Fetch Ticket Data (Optimized with staleTime & parallel fetch + auto-refetch when classifying)
  const { data: ticket, isLoading: isTicketLoading, refetch: refetchTicket } = useQuery({
    queryKey: ['ticket', id],
    queryFn: async () => (await api.get(`/tickets/${id}`)).data as Ticket,
    enabled: !!id,
    staleTime: 30000,
    gcTime: 300000,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const t = query.state.data;
      return !t || t.status === 'classifying' || t.status === 'open' ? 2000 : false;
    },
  });

  // 2. Fetch Conversation Messages (Runs in PARALLEL with ticket query + auto-refetch while AI is reading)
  const { data: conversationData, refetch: refetchMessages } = useQuery({
    queryKey: ['ticket-messages', id],
    queryFn: async () => (await api.get(`/tickets/${id}/messages`)).data as TicketConversationResponse,
    enabled: !!id,
    staleTime: 15000,
    gcTime: 300000,
    refetchOnWindowFocus: false,
    refetchInterval: () => {
      return !ticket || ticket.status === 'classifying' || ticket.status === 'open' ? 2000 : false;
    },
  });

  const isLoading = isTicketLoading && !ticket;

  const serverMessages: TicketMessage[] = conversationData?.items ?? [];
  const messages: TicketMessage[] = [...serverMessages, ...optimisticMessages];

  // Mutations (Defined before useEffect to avoid ReferenceError)
  const sendMutation = useMutation({
    mutationFn: async (content: string) =>
      (await api.post(`/tickets/${id}/messages`, { message: content })).data,
    onSuccess: () => {
      setOptimisticMessages([]);
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      refetchMessages();
      refetchTicket();
    },
    onError: (err) => {
      setOptimisticMessages([]);
      toast.error(getErrorMessage(err));
    },
  });

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, sendMutation.isPending]);

  const requestAgentMutation = useMutation({
    mutationFn: async () => (await api.post(`/tickets/${id}/request-technician`)).data,
    onSuccess: () => {
      toast.success('Đã chuyển ticket sang hàng đợi Chuyên viên hỗ trợ!');
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      refetchMessages();
      refetchTicket();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const takeoverMutation = useMutation({
    mutationFn: async () => (await api.post(`/tickets/${id}/takeover`)).data,
    onSuccess: () => {
      toast.success('Bạn đã tiếp nhận xử lý ticket này thành công!');
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      refetchMessages();
      refetchTicket();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const confirmResolutionMutation = useMutation({
    mutationFn: async (resolved: boolean) =>
      (await api.post(`/tickets/${id}/confirm-resolution?resolved=${resolved}`)).data,
    onSuccess: (_, resolved) => {
      if (resolved) {
        toast.success('Vấn đề đã được xác nhận giải quyết!');
      } else {
        toast.success('Đã gửi thông báo tới chuyên viên hỗ trợ!');
      }
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
      refetchTicket();
      refetchMessages();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const ratingMutation = useMutation({
    mutationFn: async (payload: { rating: number; feedback?: string }) =>
      (await api.post(`/tickets/${id}/rating`, payload)).data,
    onSuccess: () => {
      toast.success('Cảm ơn bạn đã gửi đánh giá trải nghiệm!');
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      refetchTicket();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const reopenMutation = useMutation({
    mutationFn: async (reason: string) =>
      (await api.post(`/tickets/${id}/reopen`, { reason })).data,
    onSuccess: () => {
      toast.success('Ticket đã được mở lại thành công!');
      setShowReopenModal(false);
      setReopenReason('');
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      queryClient.invalidateQueries({ queryKey: ['ticket-messages', id] });
      refetchTicket();
      refetchMessages();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed || sendMutation.isPending) return;

    // Optimistically render user's message immediately on screen
    const tempMsg: TicketMessage = {
      id: Date.now(),
      ticket_id: Number(id),
      sender_type: 'user',
      sender_id: user?.id ?? 1,
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    setOptimisticMessages((prev) => [...prev, tempMsg]);
    setMessage('');
    sendMutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size={36} />
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState icon="warning" title="Không tìm thấy ticket" desc="Yêu cầu hỗ trợ không tồn tại hoặc đã bị gỡ." />
      </div>
    );
  }

  const isClosedOrResolved = ['closed', 'resolved', 'rejected', 'pending_closure'].includes(ticket.status);
  const isWaitingAgent = ticket.status === 'waiting_for_agent' || ticket.status === 'escalated';
  const isHumanActive = ticket.status === 'human_active' || (ticket.assignee_id && !isClosedOrResolved);
  const isTechnician = user?.role === 'technician' || user?.role === 'manager' || user?.role === 'admin';

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Back Button Navigation Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/employee/tickets"
          className="inline-flex items-center gap-2 text-xs font-bold text-rose-600 hover:text-rose-700 tracking-wider uppercase transition-colors"
        >
          <ArrowLeft size={16} />
          <span>QUAY LẠI YÊU CẦU</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-400">Trạng thái:</span>
          <StatusBadge status={ticket.status} />
        </div>
      </div>

      {/* Main Ticket Title Container */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-sm space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {ticket.title}
          </h1>
          <span className="text-xs font-mono font-bold text-slate-400 bg-slate-100 px-3 py-1 rounded-full">
            #{ticket.ticket_number}
          </span>
        </div>
        <p className="text-xs text-slate-500 font-medium">
          Được gửi bởi bạn • Mức ưu tiên: <strong className="text-slate-700">{ticket.priority ? ticket.priority.toUpperCase() : 'MEDIUM'}</strong>
        </p>
      </div>

      {/* Riot Games Support Layout: Left Sidebar Metadata + Right Continuous Conversation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT SIDEBAR: Ticket Metadata & Agent Information (4 cols - STICKY) */}
        <aside className="lg:col-span-4 space-y-4 sticky top-20">
          
          {/* Metadata Details Card */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm space-y-5">
            <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider border-b border-slate-100 pb-3">
              Thông Tin Yêu Cầu
            </h3>

            <div className="space-y-4 text-xs">
              <div>
                <div className="text-slate-400 font-bold mb-1">MÃ YÊU CẦU</div>
                <div className="font-mono font-bold text-slate-900">{ticket.ticket_number}</div>
              </div>

              <div>
                <div className="text-slate-400 font-bold mb-1">DANH MỤC</div>
                <div className="font-bold text-slate-900">
                  {ticket.category ? CATEGORY_LABELS[ticket.category] : 'Hỗ trợ CNTT'}
                </div>
              </div>

              <div>
                <div className="text-slate-400 font-bold mb-1">MỨC ƯU TIÊN</div>
                <div>{ticket.priority ? <PriorityBadge priority={ticket.priority} /> : 'Medium'}</div>
              </div>

              <div>
                <div className="text-slate-400 font-bold mb-1">ĐÃ TẠO LÚC</div>
                <div className="text-slate-700 font-medium">{formatRelative(ticket.created_at)}</div>
              </div>

              <div>
                <div className="text-slate-400 font-bold mb-1">HOẠT ĐỘNG CUỐI</div>
                <div className="text-slate-700 font-medium">{formatRelative(ticket.updated_at)}</div>
              </div>

              {/* Dynamic Live SLA Countdown */}
              <div>
                <div className="text-slate-400 font-bold mb-1.5">CAM KẾT SLA THỜI GIAN</div>
                <DynamicSLACountdown deadline={ticket.sla_deadline} isEscalated={ticket.sla_escalated} />
              </div>
            </div>
          </div>

          {/* Assigned Agent / Support Mode Card */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm space-y-4">
            <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider border-b border-slate-100 pb-3">
              Chuyên Viên Phụ Trách
            </h3>

            {isHumanActive ? (
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-emerald-50/80 border border-emerald-200/80">
                <div className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-bold text-sm shadow-md">
                  <UserCheck size={20} />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">
                    {ticket.assignee ? ticket.assignee.full_name : 'Chuyên viên IT Support'}
                  </div>
                  <div className="text-[11px] text-emerald-700 font-semibold mt-0.5">IT Support • Technical Agent</div>
                  <div className="text-[10px] text-slate-500 mt-1">Đang trực tiếp tham gia xử lý</div>
                </div>
              </div>
            ) : isWaitingAgent ? (
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-amber-50/80 border border-amber-200/80">
                <div className="w-10 h-10 rounded-2xl bg-amber-500 text-white flex items-center justify-center font-bold text-sm shadow-md">
                  <Clock size={20} className="animate-spin" />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">Đang tìm chuyên viên</div>
                  <div className="text-[11px] text-amber-700 font-semibold mt-0.5">Ticket nằm trong hàng đợi ưu tiên</div>
                  <div className="text-[10px] text-slate-500 mt-1">Chuyên viên sẽ nhận cuộc họp sớm nhất</div>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-blue-50/80 border border-blue-200/80">
                <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-md">
                  <Bot size={20} />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">AI Support Assistant</div>
                  <div className="text-[11px] text-blue-700 font-semibold mt-0.5">Tự động tra cứu tri thức RAG</div>
                  <div className="text-[10px] text-slate-500 mt-1">Sẵn sàng handoff sang người thật khi cần</div>
                </div>
              </div>
            )}

            {/* Quick Action Buttons on Sidebar */}
            {!isClosedOrResolved && !isWaitingAgent && !isHumanActive && !isTechnician && (
              <button
                onClick={() => requestAgentMutation.mutate()}
                disabled={requestAgentMutation.isPending}
                className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-sm"
              >
                <UserPlus size={14} />
                <span>Yêu cầu gặp chuyên viên</span>
              </button>
            )}

            {/* Technician Takeover Claim Button */}
            {isTechnician && !isClosedOrResolved && (ticket.assignee_id !== user?.id) && (
              <button
                onClick={() => takeoverMutation.mutate()}
                disabled={takeoverMutation.isPending}
                className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-sm"
              >
                <UserCheck size={14} />
                <span>Tiếp nhận ticket này</span>
              </button>
            )}
          </div>

        </aside>

        {/* RIGHT AREA: Continuous Conversation Timeline & Fixed Composer (8 cols) */}
        <main className="lg:col-span-8 space-y-4">

          {/* Conversation Box */}
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden flex flex-col min-h-[580px]">
            
            {/* Timeline Header */}
            <div className="p-4 sm:p-5 bg-slate-50/80 border-b border-slate-200/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <MessageCircle size={18} className="text-blue-600" />
                <span className="text-xs font-bold text-slate-900 tracking-wide uppercase">
                  Lịch Sử Trao Đổi (Conversation Timeline)
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700">
                  {messages.length} tin nhắn
                </span>
              </div>

              {!isClosedOrResolved && (
                <button
                  onClick={() => confirmResolutionMutation.mutate(true)}
                  disabled={confirmResolutionMutation.isPending}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
                >
                  <CheckCircle2 size={14} />
                  <span>Đã giải quyết</span>
                </button>
              )}
            </div>

            {/* Message Stream — Flows naturally with page scroll */}
            <div className="flex-1 p-4 sm:p-6 space-y-6 bg-slate-50/30">
              
              {/* Ticket Original Problem Statement Card with Image Attachment Preview */}
              <ParsedDescriptionCard
                description={ticket.description}
                createdAt={ticket.created_at}
                onImageClick={(name, url) => setLightboxImage({ name, url })}
              />

              {/* Messages Mapping */}
              {messages.map((msg) => (
                <ConversationMessageItem key={msg.id} msg={msg} />
              ))}

              {/* AI Agent Real-time Typing Indicator Bubble */}
              {sendMutation.isPending && (
                <div className="flex items-start gap-3 my-2 animate-pulse">
                  <div className="w-9 h-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-sm">
                    <Bot size={18} className="animate-spin" />
                  </div>
                  <div className="p-4 rounded-3xl rounded-tl-none bg-blue-50/80 border border-blue-200/80 text-xs text-blue-900 font-semibold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                    <span>AI Support Assistant đang suy nghĩ và tổng hợp câu trả lời...</span>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Bottom Composer Area */}
            {!isClosedOrResolved ? (
              <div className="p-4 bg-white border-t border-slate-200/90 space-y-3">
                
                {/* Active Responder Indicator Banner */}
                <div className="text-[11px] font-semibold text-slate-500 flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span>
                      {isHumanActive
                        ? 'Bạn đang trao đổi trực tiếp với Chuyên viên hỗ trợ IT'
                        : isWaitingAgent
                          ? 'Đang chờ chuyên viên tiếp nhận yêu cầu...'
                          : 'AI Support Assistant đang sẵn sàng phản hồi'}
                    </span>
                  </div>
                </div>

                {/* Input Textarea & Send Buttons */}
                <div className="flex gap-2 items-end">
                  <textarea
                    rows={2}
                    placeholder={
                      isHumanActive
                        ? 'Nhập phản hồi gửi chuyên viên hỗ trợ...'
                        : 'Nhập câu hỏi hoặc phản hồi tiếp theo...'
                    }
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={sendMutation.isPending}
                    className="flex-1 p-3 bg-slate-50 border border-slate-200 rounded-2xl text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all resize-none"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!message.trim() || sendMutation.isPending}
                    className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-2xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm h-[52px]"
                  >
                    {sendMutation.isPending ? <Spinner size={16} /> : <Send size={16} />}
                    <span className="hidden sm:inline">Gửi</span>
                  </button>
                </div>
              </div>
            ) : (
              /* CLOSED TICKET: Rating Card & Reopen Trigger */
              <div className="p-6 bg-slate-50 border-t border-slate-200 space-y-6">
                
                <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-sm text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto">
                    <ShieldCheck size={28} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
                      Yêu cầu này đã được đóng
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 font-medium">
                      Vui lòng đánh giá mức độ hài lòng của bạn đối với quá trình hỗ trợ.
                    </p>
                  </div>

                  {/* 1-5 Star Rating Selector */}
                  <div className="flex items-center justify-center gap-2 pt-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => {
                          setSelectedRating(star);
                          ratingMutation.mutate({ rating: star, feedback: ratingFeedback });
                        }}
                        className="p-2 transition-transform hover:scale-110 focus:outline-none"
                      >
                        <Star
                          size={28}
                          className={
                            star <= (selectedRating || ticket.rating || 0)
                              ? 'text-amber-400 fill-amber-400'
                              : 'text-slate-300'
                          }
                        />
                      </button>
                    ))}
                  </div>

                  {/* Feedback Textarea & Submit */}
                  {selectedRating > 0 && !ticket.rating && (
                    <div className="max-w-md mx-auto space-y-3 pt-2">
                      <textarea
                        rows={2}
                        placeholder="Nhập ý kiến đóng góp của bạn (không bắt buộc)..."
                        value={ratingFeedback}
                        onChange={(e) => setRatingFeedback(e.target.value)}
                        className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        onClick={() => ratingMutation.mutate({ rating: selectedRating, feedback: ratingFeedback })}
                        disabled={ratingMutation.isPending}
                        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
                      >
                        Gửi đánh giá
                      </button>
                    </div>
                  )}

                  {/* Reopen Button */}
                  <div className="pt-4 border-t border-slate-100 flex items-center justify-center gap-3">
                    <span className="text-xs text-slate-500">Sự cố vẫn chưa được xử lý xong?</span>
                    <button
                      onClick={() => setShowReopenModal(true)}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
                    >
                      <RotateCcw size={14} />
                      <span>Mở lại yêu cầu</span>
                    </button>
                  </div>
                </div>

              </div>
            )}

          </div>

        </main>
      </div>

      {/* REOPEN TICKET MODAL */}
      {showReopenModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 space-y-5 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center">
                  <RotateCcw size={18} />
                </div>
                <h3 className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
                  Mở lại yêu cầu hỗ trợ
                </h3>
              </div>
              <button
                onClick={() => setShowReopenModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-3">
              <label className="text-xs font-bold text-slate-700 block">
                Vui lòng mô tả chi tiết lý do bạn muốn mở lại ticket: <span className="text-rose-600">*</span>
              </label>
              <textarea
                rows={4}
                placeholder="Ví dụ: Lỗi máy tính vẫn bị mất kết nối mạng sau khi khởi động lại..."
                value={reopenReason}
                onChange={(e) => setReopenReason(e.target.value)}
                className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowReopenModal(false)}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-all"
              >
                Hủy bỏ
              </button>
              <button
                onClick={() => {
                  if (!reopenReason.trim()) {
                    toast.error('Vui lòng nhập lý do mở lại ticket');
                    return;
                  }
                  reopenMutation.mutate(reopenReason);
                }}
                disabled={reopenMutation.isPending || !reopenReason.trim()}
                className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              >
                {reopenMutation.isPending ? <Spinner size={14} /> : <RotateCcw size={14} />}
                <span>Xác nhận mở lại</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* LIGHTBOX FULLSCREEN IMAGE MODAL */}
      {lightboxImage && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setLightboxImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center space-y-3" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute -top-10 right-0 text-white/80 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-all"
            >
              <X size={20} />
            </button>
            <img
              src={lightboxImage.url}
              alt={lightboxImage.name}
              className="max-h-[82vh] max-w-full rounded-2xl object-contain shadow-2xl border border-white/20"
            />
            <div className="text-xs text-white/80 font-mono bg-slate-900/80 px-4 py-1.5 rounded-full border border-white/10">
              📷 {lightboxImage.name}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Component to parse description text, attached files, and render clickable image thumbnails
function ParsedDescriptionCard({
  description,
  createdAt,
  onImageClick,
}: {
  description: string;
  createdAt: string;
  onImageClick: (name: string, url: string) => void;
}) {
  // Parse attachment tags
  const imageAttachments: { name: string; url: string }[] = [];
  const fileAttachments: string[] = [];
  const cleanDescriptionLines: string[] = [];

  const lines = description.split('\n');
  for (const line of lines) {
    if (line.includes('[Đính Kèm Ảnh:')) {
      const match = line.match(/\[Đính Kèm Ảnh:\s*([^|]+)\|([^\]]+)\]/);
      if (match) {
        imageAttachments.push({ name: match[1].trim(), url: match[2].trim() });
        continue;
      }
    }
    if (line.includes('[Đính Kèm Tệp:') || line.includes('[Đính Kèm:')) {
      const match = line.match(/\[Đính Kèm(?: Tệp)?:\s*([^\]]+)\]/);
      if (match) {
        fileAttachments.push(match[1].trim());
        continue;
      }
    }
    cleanDescriptionLines.push(line);
  }

  const cleanText = cleanDescriptionLines.join('\n').trim();

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
      <div className="text-[11px] font-extrabold text-slate-400 uppercase tracking-wider flex items-center justify-between border-b border-slate-100 pb-2">
        <span>Mô tả sự cố ban đầu từ người dùng</span>
        <span>{formatRelative(createdAt)}</span>
      </div>

      {/* Cleaned Description Text */}
      <div className="text-xs sm:text-sm text-slate-800 font-normal leading-relaxed whitespace-pre-wrap">
        {renderFormattedContent(cleanText)}
      </div>

      {/* Image Attachments Gallery */}
      {imageAttachments.length > 0 && (
        <div className="pt-3 border-t border-slate-100 space-y-2">
          <div className="text-[11px] font-bold text-slate-500 flex items-center gap-1.5">
            <span>📷 Ảnh đính kèm ({imageAttachments.length}):</span>
          </div>
          <div className="flex flex-wrap gap-3">
            {imageAttachments.map((img, idx) => (
              <div
                key={idx}
                onClick={() => onImageClick(img.name, img.url)}
                className="group relative w-32 h-24 rounded-xl overflow-hidden border border-slate-200 bg-slate-100 cursor-pointer shadow-xs hover:shadow-md transition-all hover:border-blue-400"
              >
                <img src={img.url} alt={img.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-bold gap-1">
                  <span>Phóng to</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Attachments List */}
      {fileAttachments.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2">
          {fileAttachments.map((name, idx) => (
            <span key={idx} className="px-3 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold border border-slate-200 flex items-center gap-1.5">
              📎 {name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper to parse **bold text** into bold HTML elements without raw ** asterisks
function renderFormattedContent(content: string) {
  if (!content) return null;
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const innerText = part.slice(2, -2);
      return (
        <strong key={index} className="font-extrabold text-slate-900">
          {innerText}
        </strong>
      );
    }
    return part;
  });
}

// Individual Message Card Component
function ConversationMessageItem({ msg }: { msg: TicketMessage }) {
  const isUser = msg.sender_type === 'user';
  const isAgent = msg.sender_type === 'agent';
  const isTech = msg.sender_type === 'technician';
  const isSystem = msg.sender_type === 'system';

  let sources: string[] = [];
  try {
    if (msg.sources_json) sources = JSON.parse(msg.sources_json);
  } catch {
    sources = [];
  }

  // Centered System Event Card
  if (isSystem) {
    return (
      <div className="my-4 flex items-center justify-center">
        <div className="px-4 py-2 rounded-2xl bg-slate-100 border border-slate-200/80 text-[11px] font-semibold text-slate-600 text-center max-w-md shadow-2xs leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      
      {/* Avatar Icon */}
      <div
        className={`w-9 h-9 rounded-2xl flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-sm ${
          isUser
            ? 'bg-slate-900 text-white'
            : isAgent
              ? 'bg-blue-600 text-white'
              : 'bg-emerald-600 text-white'
        }`}
      >
        {isUser ? 'U' : isAgent ? <Bot size={18} /> : <UserCheck size={18} />}
      </div>

      {/* Message Content Bubble */}
      <div className={`max-w-[80%] space-y-1 ${isUser ? 'text-right' : 'text-left'}`}>
        
        {/* Sender Name & Role Badge */}
        <div className={`text-[11px] font-bold text-slate-500 flex items-center gap-1.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span>
            {isUser ? 'Người dùng (Bạn)' : isAgent ? 'AI Support Assistant' : 'Chuyên viên IT Support'}
          </span>
          {!isUser && (
            <span className={`px-2 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider ${
              isAgent ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700'
            }`}>
              {isAgent ? 'AI Agent' : 'Human Agent'}
            </span>
          )}
        </div>

        {/* Bubble Box */}
        <div
          className={`p-4 rounded-3xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap shadow-sm border ${
            isUser
              ? 'bg-blue-600 text-white border-blue-600 rounded-tr-none'
              : isAgent
                ? 'bg-white text-slate-800 border-slate-200 rounded-tl-none'
                : 'bg-emerald-50/90 text-emerald-950 border-emerald-200/90 rounded-tl-none'
          }`}
        >
          {renderFormattedContent(msg.content)}

          {/* RAG Sources Chips */}
          {sources.length > 0 && (
            <div className="mt-3 pt-2 border-t border-slate-100 flex flex-wrap gap-1.5">
              {sources.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 flex items-center gap-1"
                >
                  <Database size={10} />
                  <span>{s}</span>
                </span>
              ))}
            </div>
          )}

          {/* AI Confidence Badge */}
          {msg.confidence_score !== null && msg.confidence_score !== undefined && isAgent && (
            <div className="mt-2 text-[10px] text-slate-400 font-medium">
              Độ tin cậy RAG: {(msg.confidence_score * 100).toFixed(0)}%
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-[10px] text-slate-400 font-medium px-1">
          {new Date(msg.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
