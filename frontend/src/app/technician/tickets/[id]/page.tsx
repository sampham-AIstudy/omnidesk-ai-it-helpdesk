'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  ArrowLeft,
  UserCheck,
  CheckCircle2,
  Building2,
  Briefcase,
  Bug,
  Siren,
  GitBranch,
  Package,
  Sparkles,
  EyeOff,
  MessageSquare,
  Paperclip,
  AtSign,
  Wand2,
  Loader2,
  Lightbulb,
  ArrowUpRight,
  UserRound,
  MessageSquareQuestion,
  TrendingUp,
  Link2,
  History,
  Check,
  Pencil,
  X,
  ChevronDown,
  AlertTriangle,
} from 'lucide-react';
import {
  MOCK_TICKET_DETAIL,
  MOCK_CONVERSATIONS,
  MOCK_RELATED_RECORDS,
  MOCK_AUDIT_LOG,
  MOCK_KB_SOURCES,
  MOCK_SUGGESTED_STEPS,
  STATUS_META,
  PRIORITY_META,
  IMPACT_META,
  TicketDetail,
  ConversationItem,
  RelatedRecord,
  AuditEntry,
  TicketStatus,
  RelatedKind,
} from '@/lib/agentWorkspaceData';

export default function AgentWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const ticketId = params?.id as string;

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [relatedRecords, setRelatedRecords] = useState<RelatedRecord[]>([]);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);

  // Composer & Filter states
  const [composerMode, setComposerMode] = useState<'public' | 'internal'>('public');
  const [composerText, setComposerText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [convFilter, setConvFilter] = useState<'all' | 'public' | 'internal'>('all');
  const [bottomTab, setBottomTab] = useState<'related' | 'audit'>('related');
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);

  // Modals state
  const [showQuickCreateModal, setShowQuickCreateModal] = useState(false);
  const [quickCreateKind, setQuickCreateKind] = useState<RelatedKind>('PROBLEM');
  const [showReassignModal, setShowReassignModal] = useState(false);
  const [selectedTech, setSelectedTech] = useState('Lê Minh Công');
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [resolutionSummary, setResolutionSummary] = useState('');
  const [resolutionReason, setResolutionReason] = useState('Đã giải quyết');
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkKind, setLinkKind] = useState<RelatedKind>('PROBLEM');
  const [linkSearchQuery, setLinkSearchQuery] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    // Simulate fetching ticket details
    setTicket({ ...MOCK_TICKET_DETAIL, id: ticketId || 'INC-10582' });
    setConversations([...MOCK_CONVERSATIONS]);
    setRelatedRecords([...MOCK_RELATED_RECORDS]);
    setAuditLog([...MOCK_AUDIT_LOG]);
    document.title = `Agent Workspace — ${ticketId || 'INC-10582'}`;
    setLoading(false);
  }, [ticketId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);

  if (loading || !ticket) {
    return (
      <div className="min-h-screen bg-[#05070d] text-white p-10 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  const statusMeta = STATUS_META[ticket.status];
  const priorityMeta = PRIORITY_META[ticket.priority];
  const impactMeta = IMPACT_META[ticket.impact];

  // Send message action
  const handleSendMessage = () => {
    if (!composerText.trim()) return;
    setIsSending(true);

    setTimeout(() => {
      const isInternal = composerMode === 'internal';
      const newItem: ConversationItem = {
        id: `msg-${Date.now()}`,
        kind: isInternal ? 'NOTE' : 'TECH',
        author: 'Lê Minh Công',
        time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        body: composerText,
        internal: isInternal,
      };

      setConversations((prev) => [...prev, newItem]);
      setComposerText('');
      setIsSending(false);

      // Add audit entry
      const newAudit: AuditEntry = {
        id: `aud-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        actor: 'Lê Minh Công',
        action: isInternal ? 'Ghi chú nội bộ' : 'Phản hồi khách hàng',
        detail: composerText.substring(0, 50) + '...',
        type: isInternal ? 'note' : 'status',
      };
      setAuditLog((prev) => [newAudit, ...prev]);

      toast.success(isInternal ? 'Đã thêm ghi chú nội bộ!' : 'Đã gửi phản hồi công khai!');
    }, 400);
  };

  // Status Change action
  const handleStatusChange = (newStatus: TicketStatus) => {
    if (newStatus === ticket.status) return;

    setTicket((prev) => (prev ? { ...prev, status: newStatus } : null));
    setStatusDropdownOpen(false);

    // Append system message & audit entry
    const newSysMsg: ConversationItem = {
      id: `msg-${Date.now()}`,
      kind: 'SYSTEM',
      author: 'System',
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      body: `Kỹ thuật viên Lê Minh Công đổi trạng thái ticket sang ${STATUS_META[newStatus].label}.`,
    };
    setConversations((prev) => [...prev, newSysMsg]);

    const newAudit: AuditEntry = {
      id: `aud-${Date.now()}`,
      timestamp: 'Vừa xong',
      actor: 'Lê Minh Công',
      action: 'Đổi trạng thái',
      detail: `Đổi trạng thái sang ${STATUS_META[newStatus].label}.`,
      type: 'status',
    };
    setAuditLog((prev) => [newAudit, ...prev]);

    toast.success(`Đã đổi trạng thái sang: ${STATUS_META[newStatus].label}`);
  };

  // Quick Create Linked Record
  const handleQuickCreateRecord = () => {
    const newIdMap: Record<RelatedKind, string> = {
      PROBLEM: `PRB-${Math.floor(1000 + Math.random() * 9000)}`,
      MAJOR_INCIDENT: `MI-${Math.floor(1000 + Math.random() * 9000)}`,
      CHANGE: `CHG-${Math.floor(1000 + Math.random() * 9000)}`,
      SERVICE_REQUEST: `REQ-${Math.floor(10000 + Math.random() * 90000)}`,
      INCIDENT: `INC-${Math.floor(10000 + Math.random() * 90000)}`,
    };

    const newRec: RelatedRecord = {
      id: newIdMap[quickCreateKind],
      kind: quickCreateKind,
      title: `${quickCreateKind} khởi tạo từ ${ticket.id}`,
      status: 'Mới tạo',
      linkedAt: 'Vừa xong',
    };

    setRelatedRecords((prev) => [newRec, ...prev]);
    setShowQuickCreateModal(false);

    // Audit log entry
    const newAudit: AuditEntry = {
      id: `aud-${Date.now()}`,
      timestamp: 'Vừa xong',
      actor: 'Lê Minh Công',
      action: 'Khởi tạo bản ghi',
      detail: `Khởi tạo ${quickCreateKind} (${newRec.id}) từ ticket.`,
      type: 'system',
    };
    setAuditLog((prev) => [newAudit, ...prev]);

    toast.success(`Đã tạo và liên kết ${quickCreateKind} (${newRec.id})!`);
  };

  // Close Ticket
  const handleCloseTicket = () => {
    if (!resolutionSummary.trim()) {
      toast.error('Vui lòng nhập tóm tắt giải pháp.');
      return;
    }

    handleStatusChange('CLOSED');
    setShowCloseModal(false);
    toast.success('Đã đóng ticket thành công!');
  };

  // Insert AI suggestion into composer
  const handleInsertAISuggestion = () => {
    const stepsText = MOCK_SUGGESTED_STEPS.map((s, idx) => `0${idx + 1}. ${s}`).join('\n');
    setComposerText((prev) => (prev ? `${prev}\n\n${stepsText}` : stepsText));
    toast.success('Đã chèn gợi ý AI vào khung phản hồi!');
  };

  // Filtered conversation items
  const filteredConversations = conversations.filter((msg) => {
    if (convFilter === 'public') return msg.kind === 'USER' || msg.kind === 'TECH' || msg.kind === 'SYSTEM';
    if (convFilter === 'internal') return msg.kind === 'NOTE' || msg.kind === 'SYSTEM' || msg.kind === 'AI';
    return true;
  });

  return (
    <div className="min-h-screen bg-[#05070d] text-white selection:bg-cyan-500/35 selection:text-white relative font-sans rounded-3xl">
      {/* Background glow orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* STICKY HEADER BAR */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#05070d]/90 backdrop-blur-xl px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        {/* Left header group */}
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/technician/queue"
            className="size-9 rounded-lg border border-white/10 bg-white/[0.03] text-white/60 hover:text-white hover:border-white/25 transition flex items-center justify-center shrink-0"
          >
            <ArrowLeft size={16} />
          </Link>

          <span className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/80 font-medium shrink-0">
            {ticket.id}
          </span>

          <h1 className="text-sm sm:text-base font-medium text-white truncate max-w-xs sm:max-w-md">
            {ticket.title}
          </h1>

          {/* Chips (hidden on small screens) */}
          <div className="hidden sm:flex items-center gap-2 shrink-0">
            <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-md ${priorityMeta.classNames}`}>
              {priorityMeta.label}
            </span>
            <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-md ${impactMeta.classNames}`}>
              {impactMeta.label}
            </span>

            {/* Clickable Status Chip */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setStatusDropdownOpen(!statusDropdownOpen)}
                className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-full border ${statusMeta.borderClass} ${statusMeta.bgClass} ${statusMeta.textClass} font-medium cursor-pointer hover:opacity-90 transition`}
              >
                <span className={`size-1.5 rounded-full ${statusMeta.dotClass}`} />
                <span>{statusMeta.label}</span>
                <ChevronDown size={12} />
              </button>

              {/* Status Dropdown */}
              {statusDropdownOpen && (
                <div className="absolute left-0 mt-2 w-44 rounded-xl border border-white/10 bg-[#0c101c] p-1.5 shadow-2xl z-40 space-y-1">
                  {(Object.keys(STATUS_META) as TicketStatus[]).map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => handleStatusChange(st)}
                      className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 hover:bg-white/10 transition cursor-pointer ${
                        ticket.status === st ? 'bg-white/10 text-cyan-300 font-semibold' : 'text-white/70'
                      }`}
                    >
                      <span className={`size-1.5 rounded-full ${STATUS_META[st].dotClass}`} />
                      <span>{STATUS_META[st].label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right header group */}
        <div className="flex items-center gap-3 shrink-0">
          {/* SLA countdown */}
          <div className="hidden md:flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-amber-300 font-medium">
              SLA: {ticket.sla.pct}% CÒN LẠI
            </span>
            <div className="w-24 h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-400 to-amber-400 rounded-full"
                style={{ width: `${ticket.sla.pct}%` }}
              />
            </div>
          </div>

          <div className="hidden md:block h-6 w-px bg-white/10" />

          {/* Action buttons */}
          <button
            type="button"
            onClick={() => setShowReassignModal(true)}
            className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white/70 hover:text-white hover:border-white/25 transition cursor-pointer inline-flex items-center gap-1.5 font-medium"
          >
            <UserCheck size={14} />
            <span>Chuyển</span>
          </button>

          <button
            type="button"
            onClick={() => setShowCloseModal(true)}
            className="rounded-lg border border-emerald-400/30 bg-emerald-400/[0.06] px-3 py-2 text-xs text-emerald-300 hover:bg-emerald-400/10 transition cursor-pointer inline-flex items-center gap-1.5 font-semibold"
          >
            <CheckCircle2 size={14} />
            <span>Đóng ticket</span>
          </button>
        </div>
      </header>

      {/* BODY CONTENT */}
      <main className="p-4 sm:p-6 space-y-6 relative z-10">
        {/* 3-COLUMN WORKSPACE GRID */}
        <div className="grid xl:grid-cols-[300px_1fr_340px] gap-4 items-start">
          {/* COLUMN 1 — TICKET PANEL */}
          <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="text-xs font-semibold text-white/70 tracking-wide uppercase">Ticket</h2>
              <span className="font-mono text-[9px] text-white/35 uppercase tracking-[0.15em]">FIELDS</span>
            </div>

            {/* Section: Requester */}
            <div>
              <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40 block mb-2">
                NGƯỜI YÊU CẦU
              </span>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-cyan-400/10 text-cyan-300 flex items-center justify-center text-sm font-semibold border border-cyan-400/20">
                  NA
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white font-medium truncate">{ticket.requester.name}</p>
                  <p className="text-[11px] text-white/45 truncate">{ticket.requester.email}</p>
                </div>
              </div>

              {/* Company & Department Chips */}
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <span className="rounded border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] text-white/55 inline-flex items-center gap-1">
                  <Building2 size={10} className="text-cyan-300" />
                  <span>{ticket.requester.department}</span>
                </span>
                <span className="rounded border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] text-white/55 inline-flex items-center gap-1">
                  <Briefcase size={10} className="text-cyan-300" />
                  <span>{ticket.requester.company}</span>
                </span>
              </div>
            </div>

            {/* Section: Information Fields */}
            <div className="pt-4 border-t border-white/10 space-y-2.5">
              <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40 block mb-1">
                THÔNG TIN CHI TIẾT
              </span>

              <div className="flex justify-between items-center text-xs">
                <span className="text-white/45">Phân loại</span>
                <span className="text-white/80 font-medium">{ticket.category}</span>
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-white/45">Mức độ khẩn cấp</span>
                <span className="text-amber-300 font-medium bg-amber-400/10 px-2 py-0.5 rounded text-[11px]">
                  {ticket.urgency}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-white/45">Asset</span>
                <span className="font-mono text-cyan-300 font-medium hover:underline cursor-pointer">
                  {ticket.asset}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-white/45">Nguồn</span>
                <span className="text-white/80 font-medium">Email Gateway</span>
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-white/45">Người tạo</span>
                <span className="text-white/80 font-medium">{ticket.createdBy}</span>
              </div>

              <div className="pt-2 flex flex-wrap gap-1">
                {ticket.tags.map((t) => (
                  <span
                    key={t}
                    className="font-mono text-[9px] uppercase tracking-wider text-cyan-300/80 bg-cyan-400/10 border border-cyan-400/20 px-1.5 py-0.5 rounded"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>

            {/* Section: SLA Card */}
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-3.5 space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs text-amber-300 font-semibold">{ticket.sla.name}</p>
                  <p className="text-[11px] text-white/45 mt-0.5">Hạn: {ticket.sla.dueAt}</p>
                </div>
                <span className="font-mono text-xs text-amber-300 font-bold">{ticket.sla.pct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-400 to-amber-400 rounded-full"
                  style={{ width: `${ticket.sla.pct}%` }}
                />
              </div>
            </div>

            {/* Section: Quick Links / Record Creation */}
            <div className="pt-4 border-t border-white/10 space-y-2">
              <span className="font-mono uppercase text-[10px] tracking-[0.15em] text-white/40 block mb-2">
                LIÊN KẾT NHANH
              </span>

              <button
                type="button"
                onClick={() => {
                  setQuickCreateKind('PROBLEM');
                  setShowQuickCreateModal(true);
                }}
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
              >
                <Bug size={14} className="text-orange-400" />
                <span>Tạo Problem</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setQuickCreateKind('MAJOR_INCIDENT');
                  setShowQuickCreateModal(true);
                }}
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-red-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
              >
                <Siren size={14} className="text-red-400" />
                <span>Nâng Major Incident</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setQuickCreateKind('CHANGE');
                  setShowQuickCreateModal(true);
                }}
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
              >
                <GitBranch size={14} className="text-blue-400" />
                <span>Tạo Change</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setQuickCreateKind('SERVICE_REQUEST');
                  setShowQuickCreateModal(true);
                }}
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
              >
                <Package size={14} className="text-emerald-400" />
                <span>Tạo Service Request</span>
              </button>
            </div>
          </section>

          {/* COLUMN 2 — CONVERSATION STREAM & COMPOSER */}
          <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl flex flex-col min-h-[620px] justify-between">
            {/* Conversation Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between gap-3">
              <h2 className="text-xs font-semibold text-white/70 uppercase">Conversation Stream</h2>

              {/* Filter Toggles */}
              <div className="flex items-center gap-1.5 bg-black/30 p-1 rounded-full border border-white/10">
                <button
                  type="button"
                  onClick={() => setConvFilter('all')}
                  className={`px-3 py-1 rounded-full text-[10px] font-medium transition cursor-pointer ${
                    convFilter === 'all'
                      ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40'
                      : 'text-white/40 hover:text-white'
                  }`}
                >
                  Tất cả
                </button>
                <button
                  type="button"
                  onClick={() => setConvFilter('public')}
                  className={`px-3 py-1 rounded-full text-[10px] font-medium transition flex items-center gap-1 cursor-pointer ${
                    convFilter === 'public'
                      ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40'
                      : 'text-white/40 hover:text-white'
                  }`}
                >
                  <MessageSquare size={12} />
                  <span>Công khai</span>
                </button>
                <button
                  type="button"
                  onClick={() => setConvFilter('internal')}
                  className={`px-3 py-1 rounded-full text-[10px] font-medium transition flex items-center gap-1 cursor-pointer ${
                    convFilter === 'internal'
                      ? 'bg-amber-400/20 text-amber-300 border border-amber-400/40'
                      : 'text-white/40 hover:text-white'
                  }`}
                >
                  <EyeOff size={12} />
                  <span>Nội bộ</span>
                </button>
              </div>
            </div>

            {/* Message List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[500px]">
              <AnimatePresence initial={false}>
                {filteredConversations.map((msg, idx) => {
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: idx * 0.04 }}
                    >
                      {/* SYSTEM MESSAGE */}
                      {msg.kind === 'SYSTEM' && (
                        <div className="text-center my-2">
                          <span className="font-mono text-[11px] text-white/35 bg-white/[0.03] px-3 py-1 rounded-full border border-white/10">
                            {msg.body}
                          </span>
                        </div>
                      )}

                      {/* USER BUBBLE (Left) */}
                      {msg.kind === 'USER' && (
                        <div className="flex justify-start">
                          <div className="bg-white/[0.05] border border-white/10 rounded-2xl rounded-tl-md p-3.5 max-w-[85%] space-y-1">
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="text-white/70 font-medium">{msg.author}</span>
                              <span className="font-mono text-[9px] text-white/35">{msg.time}</span>
                            </div>
                            <p className="text-sm text-white/80 leading-relaxed">{msg.body}</p>
                          </div>
                        </div>
                      )}

                      {/* TECH BUBBLE (Right) */}
                      {msg.kind === 'TECH' && (
                        <div className="flex justify-end">
                          <div className="bg-cyan-500/15 border border-cyan-400/25 rounded-2xl rounded-tr-md p-3.5 max-w-[85%] space-y-1">
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="font-mono text-[9px] text-cyan-300/60">
                                ĐÃ GỬI · KHÁCH HÀNG NHÌN THẤY
                              </span>
                              <span className="text-cyan-300 font-medium">{msg.author}</span>
                            </div>
                            <p className="text-sm text-white/85 leading-relaxed">{msg.body}</p>
                          </div>
                        </div>
                      )}

                      {/* INTERNAL NOTE BUBBLE (Right) */}
                      {msg.kind === 'NOTE' && (
                        <div className="flex justify-end">
                          <div className="bg-amber-400/[0.07] border border-amber-400/20 rounded-2xl rounded-tr-md p-3.5 max-w-[85%] space-y-1">
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="flex items-center gap-1 text-amber-300 font-semibold">
                                <EyeOff size={12} />
                                <span>Ghi chú nội bộ</span>
                              </span>
                              <span className="font-mono text-[9px] text-amber-300/60">
                                NỘI BỘ · KHÔNG GỬI KHÁCH
                              </span>
                            </div>
                            <p className="text-sm text-white/75 leading-relaxed">{msg.body}</p>
                          </div>
                        </div>
                      )}

                      {/* AI COPILOT BUBBLE (Left) */}
                      {msg.kind === 'AI' && (
                        <div className="flex justify-start">
                          <div className="bg-indigo-500/[0.06] border border-indigo-400/20 rounded-2xl p-3.5 max-w-[85%] space-y-1">
                            <div className="flex items-center gap-1.5 text-xs text-indigo-300 font-medium">
                              <Sparkles size={12} />
                              <span>AI Copilot</span>
                              <span className="font-mono text-[9px] text-indigo-300/50 ml-auto">GỢI Ý TỪ AI</span>
                            </div>
                            <p className="text-sm text-white/70 leading-relaxed">{msg.body}</p>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              <div ref={chatEndRef} />
            </div>

            {/* Composer Section */}
            <div className="border-t border-white/10 p-4 space-y-3">
              {/* Mode toggle */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setComposerMode('public')}
                  className={`rounded-full px-3.5 py-1.5 text-[11px] font-medium transition cursor-pointer flex items-center gap-1.5 ${
                    composerMode === 'public'
                      ? 'bg-cyan-400/15 text-cyan-300 border border-cyan-400/40 shadow-xs'
                      : 'bg-white/[0.04] text-white/50 border border-white/10 hover:text-white'
                  }`}
                >
                  <MessageSquare size={13} />
                  <span>Phản hồi công khai</span>
                </button>

                <button
                  type="button"
                  onClick={() => setComposerMode('internal')}
                  className={`rounded-full px-3.5 py-1.5 text-[11px] font-medium transition cursor-pointer flex items-center gap-1.5 ${
                    composerMode === 'internal'
                      ? 'bg-amber-400/15 text-amber-300 border border-amber-400/40 shadow-xs'
                      : 'bg-white/[0.04] text-white/50 border border-white/10 hover:text-white'
                  }`}
                >
                  <EyeOff size={13} />
                  <span>Ghi chú nội bộ</span>
                </button>
              </div>

              {/* Textarea */}
              <div className="relative">
                <textarea
                  value={composerText}
                  onChange={(e) => setComposerText(e.target.value)}
                  placeholder={
                    composerMode === 'public'
                      ? 'Viết phản hồi gửi khách hàng, tham chiếu kb:// để đính kiến thức...'
                      : 'Viết ghi chú nội bộ (chỉ kỹ thuật viên xem)...'
                  }
                  rows={3}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white placeholder:text-white/25 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 transition resize-none font-sans"
                />
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    title="Đính kèm file"
                    onClick={() => toast.success('Mở trình đính kèm file')}
                    className="size-9 rounded-lg border border-white/10 bg-white/[0.03] text-white/50 hover:text-white hover:border-white/25 transition flex items-center justify-center cursor-pointer"
                  >
                    <Paperclip size={16} />
                  </button>
                  <button
                    type="button"
                    title="Nhắc tới Asset/Ticket"
                    onClick={() => setComposerText((prev) => prev + ' @AST-0723')}
                    className="size-9 rounded-lg border border-white/10 bg-white/[0.03] text-white/50 hover:text-white hover:border-white/25 transition flex items-center justify-center cursor-pointer"
                  >
                    <AtSign size={16} />
                  </button>
                  <button
                    type="button"
                    title="AI trau chuốt phản hồi"
                    onClick={() => handleInsertAISuggestion()}
                    className="size-9 rounded-lg border border-white/10 bg-white/[0.03] text-indigo-300 hover:text-indigo-200 hover:border-indigo-400/40 transition flex items-center justify-center cursor-pointer"
                  >
                    <Wand2 size={16} />
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono text-[10px] text-white/30 hidden sm:inline">Enter ↵ GỬI</span>
                  <button
                    type="button"
                    onClick={handleSendMessage}
                    disabled={isSending || !composerText.trim()}
                    className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-blue-500 active:scale-[0.98] transition inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                  >
                    {isSending ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Đang gửi...</span>
                      </>
                    ) : (
                      <span>Gửi</span>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* COLUMN 3 — AI COPILOT */}
          <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="text-xs font-semibold text-white/70 uppercase flex items-center gap-2">
                <Sparkles size={14} className="text-indigo-300" />
                <span>AI Copilot</span>
              </h2>
              <div className="flex items-center gap-1.5 font-mono text-[9px] text-emerald-300 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded-full">
                <span className="size-1.5 bg-emerald-400 rounded-full animate-pulse" />
                <span>LIVE</span>
              </div>
            </div>

            {/* Proposed Classification */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2.5">
              <p className="text-[11px] text-white/45">Phân loại đề xuất</p>
              <p className="text-sm text-white font-medium">{ticket.category} · Authentication</p>

              <div>
                <div className="flex justify-between text-[10px] text-white/45 mb-1 font-mono">
                  <span>Độ tin cậy</span>
                  <span>87%</span>
                </div>
                <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 w-[87%]" />
                </div>
              </div>

              <div className="pt-1 flex gap-2">
                <button
                  type="button"
                  onClick={() => toast.success('Đã chấp nhận phân loại đề xuất từ AI!')}
                  className="rounded-lg bg-cyan-500/15 border border-cyan-400/40 px-3 py-1.5 text-[11px] text-cyan-300 hover:bg-cyan-400/20 transition flex items-center gap-1 cursor-pointer font-medium"
                >
                  <Check size={12} />
                  <span>Chấp nhận</span>
                </button>
                <button
                  type="button"
                  onClick={() => toast.success('Mở chỉnh sửa phân loại')}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-[11px] text-white/60 hover:text-white transition flex items-center gap-1 cursor-pointer"
                >
                  <Pencil size={12} />
                  <span>Chỉnh sửa</span>
                </button>
              </div>
            </div>

            {/* KB Sources RAG */}
            <div>
              <span className="font-mono uppercase text-[10px] text-white/40 block mb-2">KB SOURCES</span>
              <div className="space-y-2">
                {MOCK_KB_SOURCES.map((kb) => (
                  <div
                    key={kb.id}
                    onClick={() => setComposerText((prev) => `${prev} kb://${kb.id}`)}
                    className="rounded-xl border border-white/10 bg-white/[0.02] p-3 hover:border-cyan-400/40 hover:bg-white/[0.04] transition cursor-pointer group space-y-1.5"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <p className="text-xs text-white/70 font-medium group-hover:text-cyan-300 transition-colors">
                        {kb.title}
                      </p>
                      <ArrowUpRight size={12} className="text-white/30 group-hover:text-cyan-300 shrink-0" />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-white/40">
                      <span>Mức khớp {kb.matchPct}%</span>
                      <div className="h-0.5 w-16 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-400 rounded-full"
                          style={{ width: `${kb.matchPct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Suggested Fix */}
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.05] p-4 space-y-3">
              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.15em] text-cyan-300">
                <Lightbulb size={12} />
                <span>SUGGESTED FIX</span>
              </div>

              <ol className="space-y-2 list-none">
                {MOCK_SUGGESTED_STEPS.map((step, idx) => (
                  <li key={step} className="flex gap-2 text-xs text-white/70">
                    <span className="font-mono text-cyan-300/80 shrink-0 font-medium">0{idx + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>

              <div className="pt-2 border-t border-white/10 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={handleInsertAISuggestion}
                  className="rounded-lg bg-cyan-400/10 border border-cyan-400/40 px-3 py-1.5 text-[11px] text-cyan-300 hover:bg-cyan-400/20 transition cursor-pointer font-medium"
                >
                  Chèn gợi ý
                </button>
                <button
                  type="button"
                  onClick={() => toast.error('Đã phản hồi gợi ý không phù hợp.')}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-[11px] text-white/50 hover:text-white transition cursor-pointer"
                >
                  Không hợp lệ
                </button>
              </div>
            </div>

            {/* HITL Actions */}
            <div>
              <span className="font-mono uppercase text-[10px] text-white/40 block mb-2">
                HITL ACTIONS
              </span>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setShowReassignModal(true)}
                  className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
                >
                  <UserRound size={14} className="text-cyan-300" />
                  <span>Gán lại cho kỹ thuật viên</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setComposerMode('public');
                    setComposerText(
                      'Chào anh, vui lòng cung cấp thêm thông tin IP address và log file GlobalProtect.'
                    );
                    toast.success('Đã nạp mẫu yêu cầu thêm thông tin!');
                  }}
                  className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
                >
                  <MessageSquareQuestion size={14} className="text-amber-300" />
                  <span>Yêu cầu thêm thông tin</span>
                </button>

                <button
                  type="button"
                  onClick={() => toast.success('Đã chuyển ticket lên Level 3 Network Specialist!')}
                  className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs text-white/70 hover:border-cyan-400/40 hover:text-white transition flex items-center gap-2 cursor-pointer font-medium"
                >
                  <TrendingUp size={14} className="text-red-400" />
                  <span>Chuyển lên Level 3</span>
                </button>
              </div>
            </div>
          </section>
        </div>

        {/* BOTTOM SECTION — RELATED & AUDIT TIMELINE */}
        <section className="rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 space-y-4">
          {/* Tabs */}
          <div className="flex justify-between items-center border-b border-white/10 pb-3">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setBottomTab('related')}
                className={`text-xs py-1.5 px-4 rounded-full font-medium transition cursor-pointer ${
                  bottomTab === 'related'
                    ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40'
                    : 'text-white/45 hover:text-white'
                }`}
              >
                Related Records ({relatedRecords.length})
              </button>
              <button
                type="button"
                onClick={() => setBottomTab('audit')}
                className={`text-xs py-1.5 px-4 rounded-full font-medium transition cursor-pointer ${
                  bottomTab === 'audit'
                    ? 'bg-cyan-400/20 text-cyan-300 border border-cyan-400/40'
                    : 'text-white/45 hover:text-white'
                }`}
              >
                Audit Timeline ({auditLog.length})
              </button>
            </div>

            {bottomTab === 'related' && (
              <button
                type="button"
                onClick={() => setShowLinkModal(true)}
                className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3 py-1.5 text-xs text-cyan-300 hover:bg-cyan-400/20 transition flex items-center gap-1.5 cursor-pointer font-medium"
              >
                <Link2 size={14} />
                <span>Liên kết mới</span>
              </button>
            )}
          </div>

          {/* Tab 1: RELATED RECORDS GRID */}
          {bottomTab === 'related' && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {relatedRecords.map((rec) => (
                <div
                  key={rec.id}
                  className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 hover:border-cyan-400/40 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-cyan-300 font-semibold">{rec.id}</span>
                      <span className="text-[10px] text-white/50 bg-white/[0.04] px-2 py-0.5 rounded border border-white/10">
                        {rec.status}
                      </span>
                    </div>
                    <h4 className="text-xs font-medium text-white/80 mt-2 truncate">{rec.title}</h4>
                  </div>
                  <div className="mt-3 pt-2 border-t border-white/10 flex justify-between items-center text-[10px] text-white/35 font-mono">
                    <span>{rec.kind}</span>
                    <span>Liên kết: {rec.linkedAt}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 2: AUDIT TIMELINE */}
          {bottomTab === 'audit' && (
            <div className="space-y-3">
              {auditLog.map((aud) => (
                <div key={aud.id} className="flex items-start gap-3 text-xs border-b border-white/5 pb-2.5">
                  <span className="size-2 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium">{aud.actor}</span>
                      <span className="font-mono text-[10px] text-white/35">{aud.timestamp}</span>
                    </div>
                    <p className="text-white/60 mt-0.5">{aud.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* MODAL 1: QUICK CREATE LINKED RECORD */}
      <AnimatePresence>
        {showQuickCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Tạo {quickCreateKind} từ {ticket.id}</h3>
                <button type="button" onClick={() => setShowQuickCreateModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-xs text-white/60">Tiêu đề bản ghi</label>
                  <input
                    type="text"
                    defaultValue={`${quickCreateKind} liên quan đến ${ticket.title}`}
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-sm text-white font-sans focus:border-cyan-400/60 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block mb-1 text-xs text-white/60">Ghi chú tự động</label>
                  <p className="text-xs text-white/45 bg-white/[0.03] p-2.5 rounded-xl border border-white/10">
                    Bản ghi mới sẽ tự động liên kết Incident {ticket.id} và kế thừa thông tin người yêu cầu.
                  </p>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowQuickCreateModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleQuickCreateRecord}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-lg"
                >
                  Tạo bản ghi
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 2: REASSIGN TICKET */}
      <AnimatePresence>
        {showReassignModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Chuyển Ticket {ticket.id}</h3>
                <button type="button" onClick={() => setShowReassignModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div>
                <label className="block mb-1.5 text-xs text-white/60">Chọn Kỹ Thuật Viên</label>
                <select
                  value={selectedTech}
                  onChange={(e) => setSelectedTech(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#05070d] p-3 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                >
                  <option value="Lê Minh Công">Lê Minh Công (Level 2 - Network)</option>
                  <option value="Phạm Thị Dung">Phạm Thị Dung (IT Lead)</option>
                  <option value="System Admin">System Admin (Super Admin)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowReassignModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTicket((prev) => (prev ? { ...prev, assignee: selectedTech } : null));
                    setShowReassignModal(false);
                    toast.success(`Đã chuyển ticket cho ${selectedTech}!`);
                  }}
                  className="px-4 py-2 rounded-xl bg-cyan-500 text-xs font-semibold text-black hover:bg-cyan-400 transition"
                >
                  Xác nhận chuyển
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 3: CLOSE TICKET */}
      <AnimatePresence>
        {showCloseModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-emerald-400/30 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-emerald-300">Đóng Ticket {ticket.id}</h3>
                <button type="button" onClick={() => setShowCloseModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1.5 text-xs text-white/60">Lý do đóng ticket</label>
                  <select
                    value={resolutionReason}
                    onChange={(e) => setResolutionReason(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-[#05070d] p-3 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  >
                    <option value="Đã giải quyết">Đã giải quyết thành công</option>
                    <option value="Trùng lặp">Trùng lặp với ticket khác</option>
                    <option value="Không phải lỗi">Không phải lỗi hệ thống</option>
                  </select>
                </div>

                <div>
                  <label className="block mb-1.5 text-xs text-white/60">Tóm tắt giải pháp (Resolution Summary)</label>
                  <textarea
                    value={resolutionSummary}
                    onChange={(e) => setResolutionSummary(e.target.value)}
                    placeholder="Mô tả tóm tắt các bước kỹ thuật đã thực hiện để khắc phục sự cố..."
                    rows={3}
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-white placeholder:text-white/25 focus:border-cyan-400/60 focus:outline-none transition resize-none"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCloseModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleCloseTicket}
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-xs font-semibold text-black transition"
                >
                  Xác nhận đóng ticket
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL 4: LINK EXISTING RECORD */}
      <AnimatePresence>
        {showLinkModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0c101c] p-6 shadow-2xl space-y-4"
            >
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <h3 className="text-base font-semibold text-white">Tạo liên kết bản ghi mới</h3>
                <button type="button" onClick={() => setShowLinkModal(false)} className="text-white/40 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block mb-1.5 text-xs text-white/60">Loại bản ghi</label>
                  <select
                    value={linkKind}
                    onChange={(e) => setLinkKind(e.target.value as RelatedKind)}
                    className="w-full rounded-xl border border-white/10 bg-[#05070d] p-3 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  >
                    <option value="PROBLEM">PROBLEM (Vấn đề)</option>
                    <option value="MAJOR_INCIDENT">MAJOR INCIDENT (Sự cố nghiêm trọng)</option>
                    <option value="CHANGE">CHANGE (Thay đổi hạ tầng)</option>
                    <option value="SERVICE_REQUEST">SERVICE REQUEST (Yêu cầu dịch vụ)</option>
                    <option value="INCIDENT">INCIDENT (Sự cố khác)</option>
                  </select>
                </div>

                <div>
                  <label className="block mb-1.5 text-xs text-white/60">Tìm mã bản ghi có sẵn</label>
                  <input
                    type="text"
                    value={linkSearchQuery}
                    onChange={(e) => setLinkSearchQuery(e.target.value)}
                    placeholder="Ví dụ: PRB-0081, CHG-0214..."
                    className="w-full rounded-xl border border-white/10 bg-black/30 p-2.5 text-sm text-white focus:border-cyan-400/60 focus:outline-none"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowLinkModal(false)}
                  className="px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-xs text-white/70 hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!linkSearchQuery.trim()) {
                      toast.error('Vui lòng nhập mã bản ghi liên kết.');
                      return;
                    }
                    const newRec: RelatedRecord = {
                      id: linkSearchQuery.toUpperCase(),
                      kind: linkKind,
                      title: `${linkKind} liên kết thủ công`,
                      status: 'Active',
                      linkedAt: 'Vừa xong',
                    };
                    setRelatedRecords((prev) => [newRec, ...prev]);
                    setShowLinkModal(false);
                    toast.success(`Đã liên kết ${newRec.id}!`);
                  }}
                  className="px-4 py-2 rounded-xl bg-cyan-500 text-xs font-semibold text-black hover:bg-cyan-400 transition"
                >
                  Liên kết
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
