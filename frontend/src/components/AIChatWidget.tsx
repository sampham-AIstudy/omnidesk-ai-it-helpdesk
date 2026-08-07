'use client';

import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Bot, MessageSquareText, Send, X } from 'lucide-react';
import { Spinner } from './ui';
import api from '@/lib/api';

interface Message {
  sender: 'user' | 'agent';
  text: string;
  sources?: string[];
  time: string;
}

function timeLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>(() => [
    {
      sender: 'agent',
      text: 'Tôi có thể tra cứu knowledge base theo quyền của bạn và gợi ý hướng xử lý trước khi tạo ticket.',
      time: timeLabel(),
    },
  ]);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const chatMutation = useMutation({
    mutationFn: async (msg: string) => (await api.post('/chat', { message: msg })).data,
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: data.reply,
          sources: data.sources,
          time: timeLabel(),
        },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: 'Kết nối AI chưa sẵn sàng. Bạn vẫn có thể gửi ticket để hệ thống phân loại và định tuyến.',
          time: timeLabel(),
        },
      ]);
    },
  });

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || chatMutation.isPending) return;
    setInput('');
    setMessages((prev) => [...prev, { sender: 'user', text, time: timeLabel() }]);
    chatMutation.mutate(text);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen((value) => !value)}
        style={{
          position: 'fixed',
          right: 24,
          bottom: 24,
          zIndex: 60,
          height: 42,
          borderRadius: 999,
          padding: '0 16px',
          background: '#101827',
          color: '#ffffff',
          boxShadow: '0 14px 34px rgba(15,23,42,0.22)',
          display: 'flex',
          alignItems: 'center',
          gap: 9,
          fontSize: 13,
          fontWeight: 800,
          cursor: 'pointer',
        }}
      >
        <MessageSquareText size={17} />
        AI Copilot
      </button>

      {isOpen && (
        <div
          className="card"
          style={{
            position: 'fixed',
            right: 24,
            bottom: 78,
            width: 390,
            height: 520,
            zIndex: 70,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div style={{ height: 56, padding: '0 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 8, background: 'var(--primary-soft)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Bot size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: 13 }}>Help Desk Copilot</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>RAG đã lọc theo phân quyền</div>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} className="btn-ghost" style={{ width: 32, height: 32, padding: 0 }}>
              <X size={15} />
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {messages.map((message, index) => (
              <div key={index} style={{ alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '86%' }}>
                <div
                  style={{
                    borderRadius: 8,
                    padding: '9px 11px',
                    background: message.sender === 'user' ? 'var(--primary)' : 'var(--surface-muted)',
                    color: message.sender === 'user' ? '#ffffff' : 'var(--text)',
                    fontSize: 12,
                    lineHeight: 1.55,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {message.text}
                  {message.sources && message.sources.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 7, borderTop: '1px solid rgba(82,96,113,0.22)' }}>
                      <div style={{ fontSize: 10, fontWeight: 800, color: message.sender === 'user' ? '#dbeafe' : 'var(--cyan)', marginBottom: 4 }}>Nguồn KB</div>
                      {Array.from(new Set(message.sources)).slice(0, 3).map((source, sIdx) => (
                        <div key={`${source}-${sIdx}`} style={{ fontSize: 10, color: message.sender === 'user' ? '#eaf1ff' : 'var(--text-secondary)' }}>{source}</div>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ marginTop: 3, color: 'var(--text-muted)', fontSize: 10, textAlign: message.sender === 'user' ? 'right' : 'left' }}>{message.time}</div>
              </div>
            ))}
            {chatMutation.isPending && (
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--primary)', fontSize: 12, fontWeight: 800 }}>
                <Spinner size={14} />
                Đang truy vấn KB
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSend} style={{ padding: 12, borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
            <input
              className="input-field"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Hỏi về VPN, email, quyền truy cập..."
            />
            <button className="btn-primary" disabled={!input.trim() || chatMutation.isPending} style={{ width: 40, padding: 0 }}>
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
