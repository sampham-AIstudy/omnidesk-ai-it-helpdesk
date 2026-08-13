'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Bot, Check, ChevronRight, Copy, History, Plus, Send, Sparkles, Trash2, UserRound } from 'lucide-react';
import api from '@/lib/api';

type ConversationItem = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
};

const SUGGESTIONS = [
  'Hướng dẫn khắc phục lỗi không kết nối được VPN công ty',
  'Tôi cần cấp quyền truy cập một thư mục dùng chung',
  'Cách cài đặt email công ty trên điện thoại',
];

function displayDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(date);
}

function AssistantText({ content }: { content: string }) {
  return <div className="whitespace-pre-wrap break-words">{content}</div>;
}

export default function ChatbotWorkspacePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedConversation = searchParams.get('conversation');
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const response = await api.get<ConversationItem[]>('/chat/conversations');
      setConversations(response.data);
      return response.data;
    } catch {
      setError('Không thể tải lịch sử trò chuyện. Vui lòng thử lại.');
      return [];
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const selectConversation = useCallback(async (id: string, updateUrl = true) => {
    setActiveId(id);
    setLoadingConversation(true);
    setError(null);
    if (updateUrl) router.replace(`/employee/chatbot?conversation=${encodeURIComponent(id)}`);
    try {
      const response = await api.get<{ messages: ChatMessage[] }>(`/chat/conversations/${id}`);
      setMessages(response.data.messages);
    } catch {
      setMessages([]);
      setError('Không thể mở cuộc trò chuyện này. Có thể lịch sử đã được xoá.');
    } finally {
      setLoadingConversation(false);
    }
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadConversations(); }, 0);
    return () => window.clearTimeout(timer);
  }, [loadConversations]);

  useEffect(() => {
    if (!requestedConversation || requestedConversation === activeId) return;
    const timer = window.setTimeout(() => { void selectConversation(requestedConversation, false); }, 0);
    return () => window.clearTimeout(timer);
  }, [activeId, requestedConversation, selectConversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: thinking ? 'smooth' : 'auto' });
  }, [messages, thinking]);

  const startNewChat = () => {
    setActiveId(null);
    setMessages([]);
    setInput('');
    setError(null);
    router.replace('/employee/chatbot');
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const deleteConversation = async (event: React.MouseEvent<HTMLButtonElement>, id: string) => {
    event.stopPropagation();
    try {
      await api.delete(`/chat/conversations/${id}`);
      if (activeId === id) startNewChat();
      await loadConversations();
    } catch {
      setError('Không thể xoá cuộc trò chuyện. Vui lòng thử lại.');
    }
  };

  const handleSend = async (suggestion?: string) => {
    const text = (suggestion ?? input).trim();
    if (!text || thinking) return;

    setInput('');
    setError(null);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    let conversationId = activeId;

    try {
      if (!conversationId) {
        const response = await api.post<ConversationItem>('/chat/conversations', { title: text.slice(0, 60) });
        conversationId = response.data.id;
        setActiveId(conversationId);
        router.replace(`/employee/chatbot?conversation=${encodeURIComponent(conversationId)}`);
      }

      const temporaryMessage: ChatMessage = { id: `temporary-${crypto.randomUUID()}`, role: 'user', content: text };
      setMessages((current) => [...current, temporaryMessage]);
      setThinking(true);

      const response = await api.post<{ reply: string }>(`/chat/conversations/${conversationId}/messages`, { message: text });
      setMessages((current) => [...current, { id: `assistant-${crypto.randomUUID()}`, role: 'assistant', content: response.data.reply }]);
      await loadConversations();
    } catch {
      setError('Không thể gửi tin nhắn lúc này. Vui lòng thử lại sau.');
    } finally {
      setThinking(false);
    }
  };

  const copyText = async (id: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(null), 1800);
    } catch {
      setError('Không thể sao chép nội dung.');
    }
  };

  return (
    <section className="mx-auto flex h-[calc(100dvh-128px)] min-h-[620px] max-w-[1440px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <aside className="flex w-[17.5rem] shrink-0 flex-col border-r border-slate-200 bg-slate-50/80">
        <div className="border-b border-slate-200 px-4 py-4">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-blue-600 text-white shadow-sm"><Sparkles size={18} /></span>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-slate-900">AI Workspace</h1>
              <p className="mt-0.5 text-[11px] text-slate-500">Lịch sử riêng của bạn</p>
            </div>
          </div>
          <button type="button" onClick={startNewChat} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2.5 text-xs font-bold text-white transition hover:bg-slate-700 active:scale-[.98]">
            <Plus size={15} /> Cuộc trò chuyện mới
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3" aria-label="Lịch sử chat">
          <div className="mb-2 flex items-center gap-2 px-2 text-[11px] font-bold uppercase tracking-[0.08em] text-slate-400"><History size={13} /> Gần đây</div>
          {loadingHistory ? <p className="px-2 py-4 text-xs text-slate-400">Đang tải lịch sử…</p> : conversations.length === 0 ? (
            <div className="px-3 py-7 text-center text-xs leading-relaxed text-slate-400">Những cuộc trò chuyện của bạn sẽ xuất hiện tại đây.</div>
          ) : conversations.map((conversation) => {
            const active = activeId === conversation.id;
            return <div key={conversation.id} className={`group mb-1 flex items-center rounded-lg transition ${active ? 'bg-white text-blue-700 shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:bg-slate-200/70'}`}>
              <button type="button" onClick={() => void selectConversation(conversation.id)} className="min-w-0 flex-1 px-3 py-2.5 text-left">
                <span className="block truncate text-xs font-semibold">{conversation.title}</span>
                <span className="mt-1 block text-[10px] text-slate-400">{displayDate(conversation.updated_at)}</span>
              </button>
              <button type="button" onClick={(event) => void deleteConversation(event, conversation.id)} className="mr-1 grid size-7 place-items-center rounded-md text-slate-400 opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100" aria-label={`Xóa cuộc trò chuyện ${conversation.title}`}>
                <Trash2 size={14} />
              </button>
            </div>;
          })}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col bg-white">
        <header className="flex min-h-16 items-center justify-between border-b border-slate-100 px-5">
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-900">{activeId ? conversations.find((item) => item.id === activeId)?.title ?? 'Cuộc trò chuyện' : 'Cuộc trò chuyện mới'}</p>
            <p className="mt-0.5 text-[11px] text-slate-500">Được lưu an toàn trong lịch sử của bạn</p>
          </div>
          {activeId && <button type="button" onClick={startNewChat} className="hidden items-center gap-1 text-xs font-semibold text-slate-500 transition hover:text-blue-700 sm:flex">Cuộc trò chuyện mới <ChevronRight size={14} /></button>}
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {loadingConversation ? <div className="mx-auto max-w-3xl py-10 text-center text-sm text-slate-400">Đang mở cuộc trò chuyện…</div> : messages.length === 0 ? (
            <div className="mx-auto flex h-full max-w-2xl flex-col justify-center pb-8">
              <span className="mb-5 grid size-12 place-items-center rounded-2xl bg-blue-50 text-blue-600"><Sparkles size={23} /></span>
              <h2 className="max-w-xl text-balance text-2xl font-bold tracking-tight text-slate-900">Bạn cần hỗ trợ việc gì?</h2>
              <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">Hỏi về thiết bị, tài khoản, phần mềm hoặc quy trình IT. Mọi câu trả lời và lịch sử đều ở trong một workspace duy nhất.</p>
              <div className="mt-7 grid gap-2 sm:grid-cols-3">
                {SUGGESTIONS.map((suggestion) => <button key={suggestion} type="button" onClick={() => void handleSend(suggestion)} className="rounded-xl border border-slate-200 px-3 py-3 text-left text-xs font-medium leading-5 text-slate-600 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800">
                  {suggestion}
                </button>)}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.map((message) => {
                const isUser = message.role === 'user';
                return <article key={message.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
                  <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${isUser ? 'bg-slate-800 text-white' : 'bg-blue-600 text-white'}`}>{isUser ? <UserRound size={15} /> : <Bot size={16} />}</span>
                  <div className={`min-w-0 max-w-[85%] ${isUser ? 'text-right' : ''}`}>
                    <p className="mb-1 text-[11px] font-bold text-slate-400">{isUser ? 'Bạn' : 'AI Copilot'}</p>
                    <div className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${isUser ? 'rounded-tr-sm bg-slate-800 text-white' : 'rounded-tl-sm border border-slate-100 bg-slate-50 text-slate-700'}`}>
                      {isUser ? message.content : <AssistantText content={message.content} />}
                    </div>
                    {!isUser && <button type="button" onClick={() => void copyText(message.id, message.content)} className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 transition hover:text-slate-700">
                      {copiedId === message.id ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}{copiedId === message.id ? 'Đã sao chép' : 'Sao chép'}
                    </button>}
                  </div>
                </article>;
              })}
              {thinking && <div className="flex items-center gap-3 text-sm text-slate-400"><span className="grid size-8 place-items-center rounded-lg bg-blue-600 text-white"><Bot size={16} /></span><span className="inline-flex items-center gap-1.5">AI Copilot đang trả lời<span className="size-1.5 animate-pulse rounded-full bg-blue-600" /></span></div>}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {error && <div className="mx-4 mb-2 rounded-lg border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700 sm:mx-6">{error}</div>}
        <form onSubmit={(event) => { event.preventDefault(); void handleSend(); }} className="border-t border-slate-200 bg-white px-4 py-4 sm:px-6">
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 shadow-sm transition focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-50">
            <textarea ref={textareaRef} value={input} onChange={(event) => { setInput(event.target.value); event.currentTarget.style.height = 'auto'; event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 160)}px`; }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void handleSend(); } }} rows={1} placeholder="Nhắn cho AI Copilot…" className="max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400" />
            <button type="submit" disabled={!input.trim() || thinking} className="grid size-9 place-items-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Gửi tin nhắn"><Send size={16} /></button>
          </div>
          <p className="mt-2 text-center text-[10px] text-slate-400">AI có thể mắc sai sót. Hãy kiểm tra lại thông tin quan trọng.</p>
        </form>
      </main>
    </section>
  );
}
