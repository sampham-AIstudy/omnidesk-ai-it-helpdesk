'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Eye,
  EyeOff,
  FileText,
  Inbox,
  Maximize2,
  Pin,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  Wrench,
  X,
} from 'lucide-react';
import HITLModal from '@/components/HITLModal';
import TicketCard from '@/components/TicketCard';
import TicketContextMenu from '@/components/TicketContextMenu';
import AISolutionViewer from '@/components/AISolutionViewer';
import {
  ConfidenceBadge,
  EmptyState,
  PageHeader,
  PriorityBadge,
  SLABadge,
  Spinner,
  StatusBadge,
} from '@/components/ui';
import { Ticket, TicketStatus } from '@/types';
import { CATEGORY_LABELS, formatRelative, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

type ManagerFilter = 'all' | 'pending_hitl' | 'working' | 'escalated' | 'closed';

const FILTERS: { value: ManagerFilter; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'pending_hitl', label: 'Chờ duyệt HITL' },
  { value: 'working', label: 'Đang xử lý' },
  { value: 'escalated', label: 'Leo thang' },
  { value: 'closed', label: 'Đã hoàn tất' },
];

export default function ManagerTicketsPage() {
  const [filter, setFilter] = useState<ManagerFilter>('all');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [hitlTicket, setHitlTicket] = useState<Ticket | null>(null);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [activeModal, setActiveModal] = useState<'description' | 'ai_solution' | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'content' | 'properties'>('content');
  const [contextMenu, setContextMenu] = useState<{
    ticket: Ticket | null;
    position: { x: number; y: number } | null;
  }>({ ticket: null, position: null });
  const queryClient = useQueryClient();

  const pinMutation = useMutation({
    mutationFn: async ({ ticketId, is_pinned }: { ticketId: number; is_pinned: boolean }) =>
      (await api.post(`/tickets/${ticketId}/pin`, { is_pinned, pin_reason: is_pinned ? 'Ưu tiên gấp bởi Quản lý' : '' })).data,
    onSuccess: (_, vars) => {
      toast.success(vars.is_pinned ? 'Đã ghim ticket lên đầu hàng đợi 📌' : 'Đã bỏ ghim ticket');
      queryClient.invalidateQueries({ queryKey: ['manager-tickets-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket', defaultSelected] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['manager-tickets-queue'],
    queryFn: async () => {
      return (await api.get('/tickets?page=1&page_size=100')).data as {
        items: Ticket[];
        total: number;
      };
    },
    refetchInterval: 15000,
  });

  const allTickets = data?.items ?? [];

  const counts = useMemo(() => {
    return {
      all: allTickets.length,
      pending_hitl: allTickets.filter((t) => t.status === 'pending_hitl').length,
      working: allTickets.filter((t) =>
        ['in_progress', 'waiting_for_agent', 'human_active', 'reopened'].includes(t.status)
      ).length,
      escalated: allTickets.filter((t) => t.status === 'escalated').length,
      closed: allTickets.filter((t) => ['closed', 'resolved', 'rejected'].includes(t.status)).length,
    };
  }, [allTickets]);

  const tickets = useMemo(() => {
    const term = search.trim().toLocaleLowerCase('vi-VN');
    const source = allTickets.filter((ticket) => {
      if (filter === 'all') return true;
      if (filter === 'pending_hitl') return ticket.status === 'pending_hitl';
      if (filter === 'working')
        return ['in_progress', 'waiting_for_agent', 'human_active', 'reopened'].includes(ticket.status);
      if (filter === 'escalated') return ticket.status === 'escalated';
      if (filter === 'closed') return ['closed', 'resolved', 'rejected'].includes(ticket.status);
      return true;
    });

    if (!term) return source;
    return source.filter((ticket) =>
      `${ticket.ticket_number} ${ticket.title} ${ticket.description || ''} ${ticket.created_by_user?.full_name || ''} ${ticket.created_by_user?.department || ''}`
        .toLocaleLowerCase('vi-VN')
        .includes(term)
    );
  }, [allTickets, filter, search]);

  const defaultSelected = selectedId ?? tickets[0]?.id ?? null;

  const { data: selectedTicket } = useQuery({
    queryKey: ['ticket', defaultSelected],
    queryFn: async () => (await api.get(`/tickets/${defaultSelected}`)).data as Ticket,
    enabled: !!defaultSelected,
    refetchInterval: 8000,
  });

  const closeMutation = useMutation({
    mutationFn: async (ticketId: number) =>
      (
        await api.patch(`/tickets/${ticketId}/status`, {
          status: 'closed',
          note: 'Quản lý xác nhận đóng ticket sau khi kiểm tra.',
        })
      ).data,
    onSuccess: () => {
      toast.success('Ticket đã được đóng');
      queryClient.invalidateQueries({ queryKey: ['manager-tickets-queue'] });
      queryClient.invalidateQueries({ queryKey: ['ticket', defaultSelected] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div>
      <PageHeader
        title="Hàng đợi & Giám sát sự cố"
        subtitle={`${data?.total ?? 0} sự cố trong phạm vi quản lý đơn vị phụ trách`}
        action={
          <button className="btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      {/* Top Stat Cards */}
      <div className="responsive-grid-2" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 16 }}>
        <div className="stat-card">
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 6 }}>
            Tổng sự cố đơn vị
          </div>
          <div style={{ color: 'var(--primary, #2563eb)', fontSize: 26, fontWeight: 800 }}>{counts.all}</div>
        </div>

        <div className="stat-card">
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 6 }}>
            Chờ duyệt HITL
          </div>
          <div style={{ color: 'var(--amber, #f59e0b)', fontSize: 26, fontWeight: 800 }}>{counts.pending_hitl}</div>
        </div>

        <div className="stat-card">
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 6 }}>
            Đang xử lý
          </div>
          <div style={{ color: 'var(--cyan, #0891b2)', fontSize: 26, fontWeight: 800 }}>{counts.working}</div>
        </div>

        <div className="stat-card">
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 6 }}>
            Leo thang (Escalated)
          </div>
          <div style={{ color: 'var(--red, #ef4444)', fontSize: 26, fontWeight: 800 }}>{counts.escalated}</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="queue-toolbar">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {FILTERS.map((item) => (
            <button
              key={item.value}
              className={filter === item.value ? 'btn-primary' : 'btn-ghost'}
              style={{ height: 32 }}
              onClick={() => setFilter(item.value)}
            >
              {item.label}
              {counts[item.value] > 0 && ` (${counts[item.value]})`}
            </button>
          ))}
        </div>

        <label className="queue-search">
          <Search size={15} aria-hidden="true" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm mã, tiêu đề, phòng ban…"
            aria-label="Tìm sự cố"
          />
        </label>
      </div>

      {/* Main Grid */}
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
            <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 54 }}>
              <Spinner size={32} />
            </div>
          ) : tickets.length === 0 ? (
            <div className="card">
              <EmptyState icon="check" title="Không có sự cố nào" desc="Không tìm thấy sự cố nào với bộ lọc hiện tại." />
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
              <EmptyState icon="inbox" title="Chọn một sự cố" desc="Thông tin nội dung và chỉ đạo xử lý sẽ hiển thị ở đây." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Inspector Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)' }}>#{selectedTicket.ticket_number}</span>
                      <StatusBadge status={selectedTicket.status} />
                      <PriorityBadge priority={selectedTicket.priority ?? 'medium'} />
                      {selectedTicket.is_pinned && <span style={{ fontSize: 10, fontWeight: 800, color: '#92400e', background: '#fef3c7', padding: '1px 5px', borderRadius: 4 }}>📌 Top</span>}
                    </div>
                    <h3 style={{ margin: '2px 0 0', fontSize: 13.5, fontWeight: 800, lineHeight: 1.35, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                      {selectedTicket.title}
                    </h3>
                  </div>
                  <a
                    className="btn-ghost"
                    href={`/manager/tickets/${selectedTicket.id}`}
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
                    <div style={{ background: 'var(--surface-subtle)', borderRadius: 10, padding: '9px 11px', border: '1px solid var(--border-default)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                        <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <FileText size={11} /> Mô tả sự cố
                        </span>
                        <button
                          type="button"
                          onClick={() => setActiveModal('description')}
                          className="btn-ghost"
                          style={{ fontSize: 11, padding: '1px 6px', height: 20, color: 'var(--primary)', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                          title="Mở toàn màn hình mô tả sự cố"
                        >
                          <Maximize2 size={10} />
                          <span>Xem đủ</span>
                        </button>
                      </div>
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
                        }}
                        title="Nhấp để xem đầy đủ nội dung"
                      >
                        {selectedTicket.description}
                      </div>
                    </div>

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
                            style={{ fontSize: 11, padding: '1px 6px', height: 20, color: 'var(--cyan, #0891b2)', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                            title="Mở toàn màn hình giải pháp AI"
                          >
                            <Maximize2 size={10} />
                            <span>Xem đủ</span>
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
                  href={`/manager/tickets/${selectedTicket.id}`}
                  style={{ justifyContent: 'center', textDecoration: 'none', height: 32, fontSize: 12, marginTop: 2 }}
                >
                  Mở Workspace Chỉ đạo ↗
                </a>

                {/* Fast Action Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: selectedTicket.status === 'pending_hitl' ? '1fr 1fr' : '1fr 1fr', gap: 6, marginTop: 2 }}>
                  <button
                    type="button"
                    onClick={() => pinMutation.mutate({ ticketId: selectedTicket.id, is_pinned: !selectedTicket.is_pinned })}
                    className="btn-ghost"
                    style={{
                      height: 30,
                      fontSize: 11,
                      padding: '0 6px',
                      color: selectedTicket.is_pinned ? '#b45309' : 'var(--text-secondary)',
                      borderColor: selectedTicket.is_pinned ? '#f59e0b' : 'var(--border-default)',
                    }}
                    title={selectedTicket.is_pinned ? 'Bỏ ghim' : 'Ghim lên đầu'}
                  >
                    <Pin size={12} color={selectedTicket.is_pinned ? '#f59e0b' : 'currentColor'} />
                    <span>{selectedTicket.is_pinned ? 'Bỏ ghim' : 'Ghim'}</span>
                  </button>

                  {selectedTicket.status === 'pending_hitl' ? (
                    <button
                      className="btn-primary"
                      style={{ height: 30, fontSize: 11, background: 'var(--amber, #f59e0b)', borderColor: '#d97706' }}
                      onClick={() => setHitlTicket(selectedTicket)}
                    >
                      <ShieldCheck size={13} /> Duyệt HITL
                    </button>
                  ) : (
                    <button
                      className="btn-success"
                      style={{ height: 30, fontSize: 11 }}
                      disabled={closeMutation.isPending || ['closed', 'resolved', 'rejected'].includes(selectedTicket.status)}
                      onClick={() => closeMutation.mutate(selectedTicket.id)}
                    >
                      <CheckCircle2 size={13} /> Đóng
                    </button>
                  )}
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

      {hitlTicket && (
        <HITLModal
          ticket={hitlTicket}
          onClose={() => {
            setHitlTicket(null);
            refetch();
          }}
        />
      )}

      {/* Right-Click Fast Action Menu */}
      <TicketContextMenu
        ticket={contextMenu.ticket}
        position={contextMenu.position}
        onClose={() => setContextMenu({ ticket: null, position: null })}
        onTogglePin={(t) => pinMutation.mutate({ ticketId: t.id, is_pinned: !t.is_pinned })}
        isStaff={true}
      />
    </div>
  );
}
