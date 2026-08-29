'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowUpRight, Bot, MessageSquareText, Send, X } from 'lucide-react';
import api from '@/lib/api';

type ChatMessage = {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  confidence?: number | null;
};

type Conversation = {
  id: string;
  title: string;
};

type ChatReply = {
  reply: string;
  confidence?: number | null;
};

type AIChatWidgetProps = {
  showLauncher?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export default function AIChatWidget({ showLauncher = true, open, onOpenChange }: AIChatWidgetProps) {
  const router = useRouter();
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 'welcome', sender: 'agent', text: 'Tôi có thể hỗ trợ về thiết bị, tài khoản, phần mềm và các quy trình IT.' },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isOpen = open ?? uncontrolledOpen;

  const setPanelOpen = (next: boolean) => {
    if (open === undefined) setUncontrolledOpen(next);
    onOpenChange?.(next);
  };

  useEffect(() => {
    if (isOpen) bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [isOpen, messages, sending]);

  const openWorkspace = () => {
    setPanelOpen(false);
    router.push(conversationId ? `/employee/chatbot?conversation=${encodeURIComponent(conversationId)}` : '/employee/chatbot');
  };

  const handleSend = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    if (text.length > 8000) {
      setError(`Nội dung câu hỏi (${text.length.toLocaleString('vi-VN')} ký tự) vượt quá giới hạn 8.000 ký tự.`);
      return;
    }

    setInput('');
    setError(null);
    setSending(true);
    const userMessage: ChatMessage = { id: `user-${crypto.randomUUID()}`, sender: 'user', text };
    setMessages((current) => [...current, userMessage]);

    try {
      let currentId = conversationId;
      if (!currentId) {
        const response = await api.post<Conversation>('/chat/conversations', { title: text.slice(0, 60) });
        currentId = response.data.id;
        setConversationId(currentId);
      }
      const response = await api.post<ChatReply>(`/chat/conversations/${currentId}/messages`, { message: text });
      setMessages((current) => [...current, {
        id: `agent-${crypto.randomUUID()}`,
        sender: 'agent',
        text: response.data.reply,
        confidence: response.data.confidence ?? null,
      }]);
    } catch {
      setError('Không thể gửi tin nhắn. Vui lòng thử lại.');
    } finally {
      setSending(false);
    }
  };

  return <>
    {showLauncher && (
      <button onClick={() => setPanelOpen(!isOpen)} className="ai-copilot-launcher" aria-label="Mở AI Copilot" aria-expanded={isOpen}>
        <MessageSquareText size={17} aria-hidden="true" /> AI Copilot
      </button>
    )}

    {isOpen && (
      <section className="card fixed bottom-[4.875rem] right-6 z-[70] flex h-[33.75rem] w-[min(24.375rem,calc(100vw-2rem))] flex-col overflow-hidden border-slate-200 shadow-[0_18px_45px_rgba(15,23,42,0.18)]" aria-label="AI Copilot">
        <header className="flex min-h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white px-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600"><Bot size={17} /></span>
            <div className="min-w-0">
              <h2 className="truncate text-[13px] font-bold text-slate-900">AI Copilot</h2>
              <p className="truncate text-[10px] text-slate-500">Hỏi nhanh, lịch sử được lưu tự động</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button type="button" onClick={openWorkspace} className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-[11px] font-bold text-blue-700 transition hover:bg-blue-50" title="Mở toàn bộ lịch sử trong AI Workspace">
              Workspace <ArrowUpRight size={13} />
            </button>
            <button type="button" onClick={() => setPanelOpen(false)} className="grid size-8 place-items-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-800" aria-label="Đóng AI Copilot"><X size={16} /></button>
          </div>
        </header>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-slate-50/70 px-3.5 py-4">
          {messages.map((message) => {
            const isUser = message.sender === 'user';
            return <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[86%] rounded-xl px-3 py-2 text-xs leading-5 shadow-sm ${isUser ? 'rounded-br-sm bg-blue-600 text-white' : 'rounded-bl-sm border border-slate-200 bg-white text-slate-700'}`}>
                {message.text}
                {/* RAG Confidence Indicator — only shown when agent performed RAG retrieval */}
                {!isUser && message.confidence !== null && message.confidence !== undefined && (
                  <div className="mt-1.5 select-none" title={`Điểm tin cậy RAG tổng hợp: ${(message.confidence * 100).toFixed(0)}%`}>
                    <span className={`text-[9px] font-semibold ${
                      message.confidence > 0.85
                        ? 'text-emerald-500'
                        : message.confidence >= 0.40
                          ? 'text-slate-400'
                          : 'text-rose-400'
                    }`}>
                      Độ tin cậy RAG: {(message.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>;
          })}
          {sending && <div className="flex justify-start"><div className="inline-flex items-center gap-2 rounded-xl rounded-bl-sm border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-sm"><span className="size-1.5 animate-pulse rounded-full bg-blue-600" /> AI Copilot đang trả lời</div></div>}
          <div ref={bottomRef} />
        </div>

        {error && <p className="border-t border-rose-100 bg-rose-50 px-3.5 py-2 text-[11px] text-rose-700">{error}</p>}
        <form onSubmit={(event) => void handleSend(event)} className="border-t border-slate-200 bg-white p-3 space-y-1">
          <div className={`flex items-center gap-2 rounded-lg border bg-white p-1.5 transition ${input.length > 8000 ? 'border-rose-400' : 'border-slate-300 focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-50'}`}>
            <input
              value={input}
              onPaste={(e) => {
                const pasteData = e.clipboardData.getData('text');
                if (input.length + pasteData.length > 8000) {
                  setError(`Nội dung dán (${(input.length + pasteData.length).toLocaleString('vi-VN')} ký tự) vượt quá giới hạn 8.000 ký tự.`);
                }
              }}
              onChange={(event) => {
                setInput(event.target.value);
                if (event.target.value.length <= 8000 && error?.includes('8.000')) setError(null);
              }}
              placeholder="Hỏi về VPN, email, quyền truy cập…"
              className="min-w-0 flex-1 border-0 bg-transparent px-2 py-1 text-xs text-slate-800 outline-none placeholder:text-slate-400"
              aria-label="Câu hỏi cho AI Copilot"
            />
            <button type="submit" disabled={!input.trim() || sending || input.length > 8000} className="grid size-8 place-items-center rounded-md bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Gửi tin nhắn"><Send size={15} /></button>
          </div>
          <div className="flex items-center justify-between px-1 text-[10px] text-slate-400">
            <span>Lưu tự động trong Workspace</span>
            <span className={`font-mono ${input.length > 8000 ? 'font-bold text-rose-600' : input.length >= 7000 ? 'font-semibold text-amber-600' : ''}`}>
              {input.length.toLocaleString('vi-VN')} / 8.000
            </span>
          </div>
        </form>
      </section>
    )}
  </>;
}
