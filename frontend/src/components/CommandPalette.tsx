'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Siren,
  Package,
  Wrench,
  Bot,
  FileText,
  Building,
  User,
  X,
} from 'lucide-react';

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();

  // Listen for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!open) return null;

  const quickActions = [
    { label: '> Create incident', icon: Siren, action: () => router.push('/technician/tickets/INC-10582') },
    { label: '> Open AI Review', icon: Bot, action: () => router.push('/admin/ai-review') },
    { label: '> Find asset', icon: Wrench, action: () => router.push('/manager/services') },
    { label: '> Search KB', icon: FileText, action: () => router.push('/admin/rag') },
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/75 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.96 }}
          className="w-full max-w-xl rounded-2xl border border-cyan-400/40 bg-[#0c101c] p-4 shadow-2xl space-y-3 font-sans"
        >
          {/* Input Header */}
          <div className="relative flex items-center border-b border-white/10 pb-3">
            <Search size={18} className="text-cyan-300 mr-3" />
            <input
              type="text"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search everything... (INC-, REQ-, CHG-, KB-, CI: LAPTOP-)"
              className="w-full bg-transparent text-sm text-white placeholder:text-white/30 focus:outline-none"
            />
            <button type="button" onClick={() => setOpen(false)} className="text-white/40 hover:text-white">
              <X size={18} />
            </button>
          </div>

          {/* Quick Commands */}
          <div className="space-y-1">
            <span className="font-mono text-[9px] uppercase text-white/35 block px-2">COMMANDS</span>
            {quickActions.map((cmd) => {
              const CmdIcon = cmd.icon;
              return (
                <button
                  key={cmd.label}
                  type="button"
                  onClick={() => {
                    cmd.action();
                    setOpen(false);
                  }}
                  className="w-full text-left rounded-xl p-2.5 text-xs text-white/80 hover:bg-cyan-400/15 hover:text-cyan-300 transition flex items-center justify-between cursor-pointer font-mono"
                >
                  <span className="flex items-center gap-2">
                    <CmdIcon size={14} className="text-cyan-300" />
                    <span>{cmd.label}</span>
                  </span>
                  <span className="text-[10px] text-white/30">↵ Run</span>
                </button>
              );
            })}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
