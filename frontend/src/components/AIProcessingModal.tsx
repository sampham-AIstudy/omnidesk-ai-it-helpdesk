'use client';

import { useEffect, useState } from 'react';
import { Bot, CheckCircle2, Database, GitBranch, ShieldAlert } from 'lucide-react';
import { Spinner } from './ui';

interface Props {
  ticketNumber: string;
  onComplete: () => void;
}

const STEPS = [
  { id: 1, title: 'Classifier', desc: 'Đọc mô tả và gán category, priority, urgency.', icon: Bot },
  { id: 2, title: 'Knowledge retrieval', desc: 'Tìm giải pháp từ KB đã lọc theo phân quyền.', icon: Database },
  { id: 3, title: 'Safety / HITL', desc: 'Kiểm tra production, VIP, bảo mật và confidence thấp.', icon: ShieldAlert },
  { id: 4, title: 'Routing', desc: 'Định tuyến tới nhóm kỹ thuật hoặc đề xuất đóng.', icon: GitBranch },
];

export default function AIProcessingModal({ ticketNumber, onComplete }: Props) {
  const [currentStep, setCurrentStep] = useState(1);

  useEffect(() => {
    const timers = [
      window.setTimeout(() => setCurrentStep(2), 650),
      window.setTimeout(() => setCurrentStep(3), 1300),
      window.setTimeout(() => setCurrentStep(4), 2000),
      window.setTimeout(() => onComplete(), 2800),
    ];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [onComplete]);

  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ maxWidth: 560 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <div style={{ width: 42, height: 42, borderRadius: 8, background: 'var(--primary-soft)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Bot size={22} />
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase' }}>LangGraph workflow</div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>Agent đang xử lý {ticketNumber}</h2>
          </div>
        </div>

        <div style={{ display: 'grid', gap: 10 }}>
          {STEPS.map((step) => {
            const Icon = step.icon;
            const done = currentStep > step.id;
            const active = currentStep === step.id;
            return (
              <div
                key={step.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: 12,
                  borderRadius: 8,
                  border: `1px solid ${active ? 'var(--primary)' : done ? '#bce7d2' : 'var(--border)'}`,
                  background: active ? 'var(--primary-soft)' : done ? 'var(--green-soft)' : 'var(--surface-soft)',
                }}
              >
                <div style={{ width: 28, height: 28, borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', color: active ? 'var(--primary)' : done ? 'var(--green)' : 'var(--text-muted)' }}>
                  {done ? <CheckCircle2 size={18} /> : active ? <Spinner size={18} /> : <Icon size={18} />}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 800 }}>{step.title}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{step.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
