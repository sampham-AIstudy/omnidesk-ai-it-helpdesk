'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'react-hot-toast';
import { Copy, ExternalLink, Pin, Siren, UserCheck } from 'lucide-react';
import { Ticket } from '@/types';

interface Props {
  ticket: Ticket | null;
  position: { x: number; y: number } | null;
  onClose: () => void;
  onTogglePin?: (ticket: Ticket) => void;
  onTakeover?: (ticket: Ticket) => void;
  onEscalate?: (ticket: Ticket) => void;
  isStaff?: boolean;
}

export default function TicketContextMenu({
  ticket,
  position,
  onClose,
  onTogglePin,
  onTakeover,
  onEscalate,
  isStaff = false,
}: Props) {
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!position) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    const handleScroll = () => {
      onClose();
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [position, onClose]);

  if (!position || !ticket) return null;

  // Viewport boundary protection
  const menuWidth = 220;
  const menuHeight = 190;
  const adjustedX = Math.min(position.x, window.innerWidth - menuWidth - 12);
  const adjustedY = Math.min(position.y, window.innerHeight - menuHeight - 12);

  const handleCopyCode = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(ticket.ticket_number);
    toast.success(`Đã sao chép mã ${ticket.ticket_number}`);
    onClose();
  };

  const handleOpenDetail = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
    if (isStaff) {
      router.push(`/technician/tickets/${ticket.id}`);
    } else {
      router.push(`/employee/tickets/${ticket.id}`);
    }
  };

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label="Tác vụ nhanh sự cố"
      style={{
        position: 'fixed',
        left: adjustedX,
        top: adjustedY,
        zIndex: 9999,
        minWidth: menuWidth,
        background: 'var(--surface, #ffffff)',
        border: '1px solid var(--border-default, #e2e8f0)',
        borderRadius: 12,
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        padding: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      <div style={{ padding: '6px 10px', fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', marginBottom: 4 }}>
        #{ticket.ticket_number}
      </div>

      {isStaff && onTogglePin && (
        <button
          role="menuitem"
          onClick={(e) => {
            e.stopPropagation();
            onTogglePin(ticket);
            onClose();
          }}
          className="context-menu-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
            padding: '7px 10px',
            fontSize: 13,
            fontWeight: 600,
            border: 'none',
            background: 'transparent',
            borderRadius: 6,
            cursor: 'pointer',
            textAlign: 'left',
            color: ticket.is_pinned ? '#b45309' : 'var(--text-primary)',
          }}
        >
          <Pin size={15} color={ticket.is_pinned ? '#f59e0b' : 'currentColor'} />
          <span>{ticket.is_pinned ? 'Bỏ ghim ưu tiên' : '📌 Ghim lên đầu hàng đợi'}</span>
        </button>
      )}

      {isStaff && onTakeover && !ticket.assignee_id && !['closed', 'resolved'].includes(ticket.status) && (
        <button
          role="menuitem"
          onClick={(e) => {
            e.stopPropagation();
            onTakeover(ticket);
            onClose();
          }}
          className="context-menu-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
            padding: '7px 10px',
            fontSize: 13,
            fontWeight: 600,
            border: 'none',
            background: 'transparent',
            borderRadius: 6,
            cursor: 'pointer',
            textAlign: 'left',
            color: 'var(--text-primary)',
          }}
        >
          <UserCheck size={15} color="#2563eb" />
          <span>Tiếp nhận ticket này</span>
        </button>
      )}

      {isStaff && onEscalate && !['closed', 'resolved'].includes(ticket.status) && (
        <button
          role="menuitem"
          onClick={(e) => {
            e.stopPropagation();
            onEscalate(ticket);
            onClose();
          }}
          className="context-menu-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
            padding: '7px 10px',
            fontSize: 13,
            fontWeight: 600,
            border: 'none',
            background: 'transparent',
            borderRadius: 6,
            cursor: 'pointer',
            textAlign: 'left',
            color: '#dc2626',
          }}
        >
          <Siren size={15} />
          <span>Leo thang khẩn cấp</span>
        </button>
      )}

      <button
        role="menuitem"
        onClick={handleCopyCode}
        className="context-menu-item"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          width: '100%',
          padding: '7px 10px',
          fontSize: 13,
          fontWeight: 600,
          border: 'none',
          background: 'transparent',
          borderRadius: 6,
          cursor: 'pointer',
          textAlign: 'left',
          color: 'var(--text-primary)',
        }}
      >
        <Copy size={15} />
        <span>Sao chép mã ticket</span>
      </button>

      <button
        role="menuitem"
        onClick={handleOpenDetail}
        className="context-menu-item"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          width: '100%',
          padding: '7px 10px',
          fontSize: 13,
          fontWeight: 600,
          border: 'none',
          background: 'transparent',
          borderRadius: 6,
          cursor: 'pointer',
          textAlign: 'left',
          color: 'var(--primary, #2563eb)',
        }}
      >
        <ExternalLink size={15} />
        <span>Mở chi tiết ticket ↗</span>
      </button>
    </div>
  );
}
