'use client';

import { useMemo, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Siren,
  Package,
  Wrench,
  Bot,
  FileText,
  BookOpen,
  ClipboardList,
  Gauge,
  Inbox,
  X,
} from 'lucide-react';
import { useAuthStore } from '@/lib/authStore';

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();
  const { user } = useAuthStore();

  // Listen for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    const openPalette = () => setOpen(true);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('omnidesk:open-command-palette', openPalette);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('omnidesk:open-command-palette', openPalette);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [open]);

  const quickActions = useMemo(() => {
    if (user?.role === 'employee') return [
      { label: 'Tạo ticket sự cố', keywords: 'incident support help', icon: Siren, href: '/employee/new-ticket' },
      { label: 'Sự cố của tôi', keywords: 'ticket incident status', icon: Inbox, href: '/employee/tickets' },
      { label: 'Danh mục dịch vụ CNTT', keywords: 'catalog request service', icon: Package, href: '/employee/catalog' },
      { label: 'Tra cứu trung tâm tri thức', keywords: 'knowledge kb article', icon: BookOpen, href: '/employee/kb' },
    ];
    if (user?.role === 'technician') return [
      { label: 'Hàng đợi sự cố', keywords: 'queue incident', icon: Inbox, href: '/technician/queue' },
      { label: 'Yêu cầu dịch vụ cần xử lý', keywords: 'service request fulfillment', icon: ClipboardList, href: '/technician/requests' },
    ];
    return [
      { label: 'Hàng đợi đánh giá AI', keywords: 'ai review', icon: Bot, href: '/admin/ai-review' },
      { label: 'Knowledge base', keywords: 'knowledge kb', icon: FileText, href: '/admin/kb' },
      { label: 'Tình trạng hệ thống', keywords: 'system health', icon: Wrench, href: '/admin/system-health' },
    ];
  }, [user?.role]);
  const filteredActions = quickActions.filter((item) => `${item.label} ${item.keywords}`.toLowerCase().includes(query.trim().toLowerCase()));

  if (!open) return null;

  return (
    <AnimatePresence>
      <div className="modal-overlay command-palette-overlay" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.96 }}
          className="command-palette"
        >
          {/* Input Header */}
          <div className="relative flex items-center border-b border-white/10 pb-3">
            <Search size={18} className="text-cyan-300 mr-3" />
            <input
              type="text"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Tìm trang hoặc thao tác…"
              className="w-full bg-transparent text-sm text-white placeholder:text-white/30 focus:outline-none"
            />
            <button type="button" onClick={() => setOpen(false)} className="text-white/40 hover:text-white">
              <X size={18} />
            </button>
          </div>

          {/* Quick Commands */}
          <div className="space-y-1">
            <span className="font-mono text-[9px] uppercase text-white/35 block px-2">THAO TÁC NHANH</span>
            {filteredActions.map((cmd) => {
              const CmdIcon = cmd.icon;
              return (
                <button
                  key={cmd.label}
                  type="button"
                  onClick={() => {
                    router.push(cmd.href);
                    setOpen(false);
                  }}
                  className="w-full text-left rounded-xl p-2.5 text-xs text-white/80 hover:bg-cyan-400/15 hover:text-cyan-300 transition flex items-center justify-between cursor-pointer font-mono"
                >
                  <span className="flex items-center gap-2">
                    <CmdIcon size={14} className="text-cyan-300" />
                    <span>{cmd.label}</span>
                  </span>
                  <span className="text-[10px] text-white/30">Mở</span>
                </button>
              );
            })}
            {filteredActions.length === 0 && <p className="px-2 py-5 text-center text-xs text-white/45">Không tìm thấy thao tác phù hợp.</p>}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
