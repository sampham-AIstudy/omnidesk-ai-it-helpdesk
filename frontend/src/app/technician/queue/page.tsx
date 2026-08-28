'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { BookOpen, CheckCircle2, ChevronDown, ChevronRight, ExternalLink, Eye, EyeOff, FileText, Maximize2, Pin, RefreshCw, Search, Siren, Sparkles, Wrench, X } from 'lucide-react';
import TicketCard from '@/components/TicketCard';
import TicketContextMenu from '@/components/TicketContextMenu';
import AISolutionViewer from '@/components/AISolutionViewer';
import EscalateModal from '@/components/EscalateModal';
import { ConfidenceBadge, EmptyState, PageHeader, PriorityBadge, SLABadge, Spinner, StatusBadge } from '@/components/ui';
import { Ticket, TicketStatus } from '@/types';
import { CATEGORY_LABELS, extractTicketStructuredDescription, formatRelative, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

type QueueFilter = 'all' | 'open' | 'classifying' | 'pending_hitl' | 'working' | 'escalated';
const FILTERS: { value: QueueFilter; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'open', label: 'Mới' },
  { value: 'classifying', label: 'AI đang đọc' },
  { value: 'pending_hitl', label: 'Chờ HITL' },
  { value: 'working', label: 'Đang xử lý' },
  { value: 'escalated', label: 'Leo thang' },
];

export default function TechQueuePage() {
  const [filter, setFilter] = useState<QueueFilter>('all');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [activeModal, setActiveModal] = useState<'description' | 'ai_solution' | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'content' | 'properties'>('content');
  const [escalatingTicket, setEscalatingTicket] = useState<Ticket | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    ticket: Ticket | null;
    position: { x: number; y: number } | null;
  }>({ ticket: null, position: null });
  const queryClient = useQueryClient();

  const pinMutation = useMutation({
    mutationFn: async ({ ticketId, is_pinned }: { ticketId: number; is_pinned: boolean }) =>
      (await api.post(`/tickets/${ticketId}/pin`, { is_pinned, pin_reason: is_pinned ? 'Ưu tiên gấp bởi Kỹ thuật viên' : '' })).data,
    onSuccess: (_, vars) => {
      toast.success(vars.is_pinned ? 'Đã ghim ticket lên đầu hàng đợi 📌' : 'Đã bỏ ghim ticket');
      queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tech-queue'],
    queryFn: async () => {
      return (await api.get('/tickets?page=1&page_size=100')).data as { items: Ticket[]; total: number };
    },
    refetchInterval: 12000,
  });

  const tickets = useMemo(() => {
    const term = search.trim().toLocaleLowerCase('vi-VN');
    const source = (data?.items ?? []).filter((ticket) => {
      if (filter === 'all') return true;
      if (filter === 'working') return ['in_progress', 'waiting_for_agent', 'human_active', 'reopened'].includes(ticket.status);
      return ticket.status === filter;
    });
    if (!term) return source;
    return source.filter((ticket) => `${ticket.ticket_number} ${ticket.title} ${ticket.description}`.toLocaleLowerCase('vi-VN').includes(term));
  }, [data, filter, search]);
  const defaultSelected = selectedId ?? tickets[0]?.id ?? null;

  const { data: selectedTicket } = useQuery({
    queryKey: ['ticket', defaultSelected],
    queryFn: async () => (await api.get(`/tickets/${defaultSelected}`)).data as Ticket,
    enabled: !!defaultSelected,
    refetchInterval: 6000,
  });

  const closeMutation = useMutation({
    mutationFn: async (ticketId: number) => (await api.patch(`/tickets/${ticketId}/status`, { status: 'closed', note: 'Kỹ thuật viên xác nhận đã xử lý.' })).data,
    onSuccess: () => {
      toast.success('Ticket đã đóng');
      queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const counts = useMemo(() => ({
    urgent: tickets.filter((ticket) => ticket.priority === 'critical' || ticket.sla_escalated).length,
    hitl: tickets.filter((ticket) => ticket.status === 'pending_hitl').length,
    lowConfidence: tickets.filter((ticket) => (ticket.confidence_score ?? 1) < 0.6).length,
  }), [tickets]);

  let ragSources: Array<string | { label?: string; url?: string; kind?: string }> = [];
  try {
    const parsed = JSON.parse(selectedTicket?.rag_sources ?? '[]');
    ragSources = Array.isArray(parsed) ? parsed : [];
  } catch {
    ragSources = [];
  }

  return (
    <div>
      <PageHeader
        title="Workbench kỹ thuật viên"
        subtitle={`${data?.total ?? 0} ticket trong hàng đợi theo quyền công ty/phòng ban`}
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      <div className="responsive-grid-2" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'Khẩn cấp / escalated', value: counts.urgent, color: 'var(--red)' },
          { label: 'Chờ HITL', value: counts.hitl, color: 'var(--amber)' },
          { label: 'Confidence thấp', value: counts.lowConfidence, color: 'var(--violet)' },
        ].map((item) => (
          <div key={item.label} className="stat-card">
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 8 }}>{item.label}</div>
            <div style={{ color: item.color, fontSize: 26, fontWeight: 800 }}>{item.value}</div>
          </div>
        ))}
      </div>

      <div className="queue-toolbar">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {FILTERS.map((item) => (
            <button key={item.value} className={filter === item.value ? 'btn-primary' : 'btn-ghost'} style={{ height: 32 }} onClick={() => setFilter(item.value)}>
              {item.label}
            </button>
          ))}
        </div>
        <label className="queue-search">
          <Search size={15} aria-hidden="true" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tìm ticket, tiêu đề…" aria-label="Tìm trong hàng đợi" />
        </label>
      </div>

      <div className="workbench-grid" style={{ gridTemplateColumns: showRightPanel ? 'minmax(0, 1fr) 330px' : '1fr', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>
              Hiển thị {tickets.length} sự cố • Nhấp chuột phải để mở menu thao tác nhanh
            </span>
            <button
              type="button"
              onClick={() => setShowRightPanel(!showRightPanel)}
              className="btn-ghost"
              style={{ fontSize: 12, height: 28, padding: '0 8px', display: 'inline-flex', alignItems: 'center', gap: 5 }}
            >
              {showRightPanel ? <EyeOff size={13} /> : <Eye size={13} />}
              <span>{showRightPanel ? 'Ẩn thanh xem nhanh' : 'Hiện thanh xem nhanh'}</span>
            </button>
          </div>

          {isLoading ? (
            <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div>
          ) : tickets.length === 0 ? (
            <div className="card">
              <EmptyState icon="check" title="Hàng đợi trống" desc="Không có ticket cần xử lý với bộ lọc hiện tại." />
            </div>
          ) : (
            tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                queue
                selected={selectedTicket?.id === ticket.id}
                onClick={() => setSelectedId(ticket.id)}
                onTogglePin={(t) => pinMutation.mutate({ ticketId: t.id, is_pinned: !t.is_pinned })}
                onContextMenu={(e, t) => setContextMenu({ ticket: t, position: { x: e.clientX, y: e.clientY } })}
              />
            ))
          )}
        </div>

        {/* Streamlined Compact Right Inspector Panel (Linear / Intercom style with Tabs) */}
        {showRightPanel && (
          <aside className="card queue-detail-panel" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10, position: 'sticky', top: 80, height: 'fit-content' }}>
            {!selectedTicket ? (
              <EmptyState icon="inbox" title="Chọn một ticket" desc="Thông tin nội dung và thao tác nhanh sẽ hiển thị ở đây." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Inspector Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)' }}>#{selectedTicket.ticket_number}</span>
                      <StatusBadge status={selectedTicket.status} />
                      {selectedTicket.priority && <PriorityBadge priority={selectedTicket.priority} />}
                      {selectedTicket.is_pinned && <span style={{ fontSize: 10, fontWeight: 800, color: '#92400e', background: '#fef3c7', padding: '1px 5px', borderRadius: 4 }}>📌 Top</span>}
                    </div>
                    <h3 style={{ margin: '2px 0 0', fontSize: 13.5, fontWeight: 800, lineHeight: 1.35, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                      {selectedTicket.title}
                    </h3>
                  </div>
                  <a
                    className="btn-ghost"
                    href={`/technician/tickets/${selectedTicket.id}`}
                    style={{ width: 28, height: 28, padding: 0, flexShrink: 0 }}
                    title="Mở toàn màn hình"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>

                {/* Tab Switcher: Nội dung & AI vs Thuộc tính */}
                <div style={{ display: 'flex', gap: 4, padding: 3, background: 'var(--surface-subtle)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                  <button
                    type="button"
                    onClick={() => setInspectorTab('content')}
                    style={{
                      flex: 1,
                      padding: '5px 8px',
                      fontSize: 11.5,
                      fontWeight: 700,
                      borderRadius: 6,
                      border: 'none',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 5,
                      background: inspectorTab === 'content' ? 'var(--surface)' : 'transparent',
                      color: inspectorTab === 'content' ? 'var(--primary)' : 'var(--text-muted)',
                      boxShadow: inspectorTab === 'content' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      transition: 'all 120ms ease',
                    }}
                  >
                    <Sparkles size={12} color={inspectorTab === 'content' ? 'var(--primary)' : 'currentColor'} />
                    <span>Nội dung & AI</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setInspectorTab('properties')}
                    style={{
                      flex: 1,
                      padding: '5px 8px',
                      fontSize: 11.5,
                      fontWeight: 700,
                      borderRadius: 6,
                      border: 'none',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 5,
                      background: inspectorTab === 'properties' ? 'var(--surface)' : 'transparent',
                      color: inspectorTab === 'properties' ? 'var(--primary)' : 'var(--text-muted)',
                      boxShadow: inspectorTab === 'properties' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      transition: 'all 120ms ease',
                    }}
                  >
                    <FileText size={12} color={inspectorTab === 'properties' ? 'var(--primary)' : 'currentColor'} />
                    <span>Thuộc tính</span>
                  </button>
                </div>

                {/* Tab 1: Nội dung & Đề xuất AI */}
                {inspectorTab === 'content' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {/* Clean Description Preview Card */}
                    {(() => {
                      const { cleanText, specs } = extractTicketStructuredDescription(selectedTicket.description);
                      return (
                        <div style={{ background: 'var(--surface-subtle)', borderRadius: 10, padding: '9px 11px', border: '1px solid var(--border-default)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                            <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
                              <FileText size={11} /> Mô tả sự cố
                            </span>
                            <button
                              type="button"
                              onClick={() => setActiveModal('description')}
                              className="btn-ghost"
                              style={{ width: 22, height: 22, padding: 0, color: 'var(--text-muted)', display: 'grid', placeItems: 'center', borderRadius: 4 }}
                              title="Mở toàn màn hình mô tả sự cố"
                            >
                              <Maximize2 size={12} />
                            </button>
                          </div>

                          {specs.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                              {specs.slice(0, 3).map((s, idx) => (
                                <span key={idx} style={{ fontSize: 10, padding: '1px 5px', background: 'var(--surface)', border: '1px solid var(--border-subtle)', borderRadius: 4, color: 'var(--text-secondary)' }}>
                                  <strong style={{ color: 'var(--text-muted)' }}>{s.label.split('/')[0].trim()}:</strong> {s.value.length > 22 ? s.value.slice(0, 22) + '…' : s.value}
                                </span>
                              ))}
                            </div>
                          )}

                          <div
                            onClick={() => setActiveModal('description')}
                            style={{
                              fontSize: 12,
                              color: 'var(--text-secondary)',
                              lineHeight: 1.45,
                              cursor: 'pointer',
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              fontWeight: 500,
                            }}
                            title="Nhấp để xem đầy đủ nội dung"
                          >
                            {cleanText}
                          </div>
                        </div>
                      );
                    })()}

                    {/* Clean AI Suggestions Card */}
                    {selectedTicket.suggested_solution ? (
                      <div style={{ background: '#f8fcff', borderRadius: 10, padding: '9px 11px', border: '1px solid #b7e8f2' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                          <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--cyan, #0891b2)', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Sparkles size={11} /> Đề xuất AI
                          </span>
                          <button
                            type="button"
                            onClick={() => setActiveModal('ai_solution')}
                            className="btn-ghost"
                            style={{ width: 22, height: 22, padding: 0, color: 'var(--cyan, #0891b2)', display: 'grid', placeItems: 'center', borderRadius: 4 }}
                            title="Mở toàn màn hình giải pháp AI"
                          >
                            <Maximize2 size={12} />
                          </button>
                        </div>
                        <div
                          onClick={() => setActiveModal('ai_solution')}
                          style={{
                            fontSize: 12,
                            color: 'var(--text-secondary)',
                            lineHeight: 1.45,
                            cursor: 'pointer',
                            display: '-webkit-box',
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                          title="Nhấp để xem toàn bộ phân tích AI"
                        >
                          {selectedTicket.suggested_solution}
                        </div>

                        {ragSources.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 4, marginTop: 8, paddingTop: 6, borderTop: '1px solid #e0f2fe' }}>
                            <span style={{ fontSize: 10, fontWeight: 800, color: '#0369a1', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 3 }}>
                              <BookOpen size={10} /> Nguồn:
                            </span>
                            {ragSources.map((source, idx) => {
                              const label = typeof source === 'string' ? source : source?.label || source?.url || 'Nguồn RAG';
                              const url = typeof source === 'object' && source?.url ? source.url : '';
                              const isUrl = Boolean(url && url.startsWith('http')) || label.startsWith('http');
                              const targetUrl = isUrl ? (url || label) : '';
                              return (
                                <button
                                  key={idx}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (targetUrl) {
                                      window.open(targetUrl, '_blank');
                                    } else {
                                      setActiveModal('ai_solution');
                                    }
                                  }}
                                  style={{
                                    fontSize: 10.5,
                                    padding: '2px 7px',
                                    borderRadius: 5,
                                    background: '#ffffff',
                                    border: '1px solid #bae6fd',
                                    color: '#0284c7',
                                    fontWeight: 700,
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: 3,
                                    cursor: 'pointer',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                                  }}
                                  title={targetUrl ? 'Mở liên kết ngoài' : 'Bấm để xem chi tiết bài viết tri thức này'}
                                >
                                  <span>{label.replace(/[\[\]]/g, '')}</span>
                                  <ExternalLink size={9} style={{ opacity: 0.7 }} />
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ padding: '8px 10px', background: 'var(--surface-subtle)', borderRadius: 8, fontSize: 11.5, color: 'var(--text-muted)', textAlign: 'center' }}>
                        Chưa có đề xuất giải pháp tự động
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Thuộc tính Kỹ thuật */}
                {inspectorTab === 'properties' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 7, padding: '8px 0', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                      <span style={{ color: 'var(--text-muted)' }}>Hạn SLA</span>
                      <SLABadge deadline={selectedTicket.sla_deadline} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                      <span style={{ color: 'var(--text-muted)' }}>Người gửi</span>
                      {(() => {
                        const userObj = selectedTicket.created_by_user || selectedTicket.submitter;
                        const name = userObj?.full_name || (selectedTicket.submitter_id ? `Nhân viên #${selectedTicket.submitter_id}` : 'Người dùng');
                        const dept = userObj?.department;
                        return (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5, maxWidth: 180 }}>
                            <div style={{ width: 18, height: 18, borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 9.5, fontWeight: 800, flexShrink: 0 }}>
                              {name.slice(0, 1)}
                            </div>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={`${name}${dept ? ` (${dept})` : ''}`}>
                              {name}{dept ? ` (${dept})` : ''}
                            </span>
                          </div>
                        );
                      })()}
                    </div>

                    {selectedTicket.category && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Phân loại</span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)' }}>
                          {CATEGORY_LABELS[selectedTicket.category]}
                        </span>
                      </div>
                    )}

                    {selectedTicket.routing_target && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Định tuyến</span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#047857' }}>
                          🎯 {selectedTicket.routing_target}
                        </span>
                      </div>
                    )}

                    {selectedTicket.confidence_score != null && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                        <span style={{ color: 'var(--text-muted)' }}>Tin cậy AI</span>
                        <ConfidenceBadge score={selectedTicket.confidence_score} />
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: 'var(--text-muted)', paddingTop: 2 }}>
                      <span>Thời gian tạo</span>
                      <span>{formatRelative(selectedTicket.created_at)}</span>
                    </div>
                  </div>
                )}

                {/* Primary CTA Button */}
                <a
                  className="btn-primary"
                  href={`/technician/tickets/${selectedTicket.id}`}
                  style={{ justifyContent: 'center', textDecoration: 'none', height: 32, fontSize: 12, marginTop: 2 }}
                >
                  Mở Workspace Xử lý ↗
                </a>

                {/* Fast Action Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                  <button
                    type="button"
                    onClick={() => pinMutation.mutate({ ticketId: selectedTicket.id, is_pinned: !selectedTicket.is_pinned })}
                    className="btn-ghost"
                    style={{
                      height: 28,
                      fontSize: 11,
                      padding: '0 4px',
                      color: selectedTicket.is_pinned ? '#b45309' : 'var(--text-secondary)',
                      borderColor: selectedTicket.is_pinned ? '#f59e0b' : 'var(--border-default)',
                    }}
                    title={selectedTicket.is_pinned ? 'Bỏ ghim' : 'Ghim lên đầu'}
                  >
                    <Pin size={12} color={selectedTicket.is_pinned ? '#f59e0b' : 'currentColor'} />
                    <span>{selectedTicket.is_pinned ? 'Bỏ ghim' : 'Ghim'}</span>
                  </button>

                  <button
                    className="btn-success"
                    style={{ height: 28, fontSize: 11, padding: '0 4px' }}
                    disabled={closeMutation.isPending || !['open', 'in_progress'].includes(selectedTicket.status)}
                    onClick={() => closeMutation.mutate(selectedTicket.id)}
                  >
                    <CheckCircle2 size={12} />
                    <span>Đóng</span>
                  </button>

                  <button
                    className="btn-danger"
                    style={{ height: 28, fontSize: 11, padding: '0 4px' }}
                    disabled={selectedTicket.status === 'closed' || selectedTicket.status === 'resolved'}
                    onClick={() => setEscalatingTicket(selectedTicket)}
                  >
                    <Siren size={12} />
                    <span>Leo thang</span>
                  </button>
                </div>
              </div>
            )}
          </aside>
        )}
      </div>

      {/* Reader Modal for Full Description & AI Solution */}
      {activeModal && selectedTicket && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(4px)',
            zIndex: 100,
            display: 'grid',
            placeItems: 'center',
            padding: 16,
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: 680,
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              padding: 0,
              overflow: 'hidden',
              boxShadow: '0 24px 48px rgba(0,0,0,0.3)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                {activeModal === 'description' ? <FileText size={18} color="var(--primary)" /> : <Sparkles size={18} color="var(--cyan)" />}
                <div>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>
                    {activeModal === 'description' ? 'Chi tiết mô tả sự cố' : 'Phân tích & Đề xuất giải pháp AI'}
                  </h3>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    #{selectedTicket.ticket_number} • {selectedTicket.title}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="btn-ghost"
                style={{ width: 30, height: 30, padding: 0, borderRadius: '50%' }}
                aria-label="Đóng"
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
              <AISolutionViewer content={activeModal === 'description' ? selectedTicket.description : selectedTicket.suggested_solution} />
            </div>

            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 8, background: 'var(--surface-subtle)' }}>
              <button type="button" onClick={() => setActiveModal(null)} className="btn-secondary" style={{ height: 32, fontSize: 12 }}>
                Đóng cửa sổ
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Escalate Modal */}
      {escalatingTicket && (
        <EscalateModal
          ticket={escalatingTicket}
          onClose={() => setEscalatingTicket(null)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['tech-queue'] });
            queryClient.invalidateQueries({ queryKey: ['ticket'] });
          }}
        />
      )}

      {/* Right-Click Fast Action Menu */}
      <TicketContextMenu
        ticket={contextMenu.ticket}
        position={contextMenu.position}
        onClose={() => setContextMenu({ ticket: null, position: null })}
        onTogglePin={(t) => pinMutation.mutate({ ticketId: t.id, is_pinned: !t.is_pinned })}
        onEscalate={(t) => setEscalatingTicket(t)}
        isStaff={true}
      />
    </div>
  );
}
