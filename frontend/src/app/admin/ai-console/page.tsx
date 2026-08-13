'use client';

import { useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import { Bot, CheckCircle2, CircleAlert, Cpu, ShieldCheck, ThumbsDown, ThumbsUp, Timer } from 'lucide-react';
import { PageHeader } from '@/components/ui';

type ExecutionMode = 'copilot' | 'supervised';
type RunStatus = 'completed' | 'review';

type AgentRun = {
  id: string;
  ticket: string;
  action: string;
  confidence: number;
  duration: string;
  status: RunStatus;
  reviewed?: 'helpful' | 'unsafe';
};

const INITIAL_RUNS: AgentRun[] = [
  { id: 'AI-991', ticket: 'HD-9941', action: 'Đề xuất quy trình mở khóa Entra ID và xác minh OTP.', confidence: 0.985, duration: '1.2s', status: 'completed' },
  { id: 'AI-992', ticket: 'HD-9945', action: 'Nháp yêu cầu cấp quyền SharePoint cho nhóm Kế toán.', confidence: 0.95, duration: '2.4s', status: 'review' },
  { id: 'AI-993', ticket: 'HD-9948', action: 'Tóm tắt sự cố VPN và đính kèm 3 nguồn Knowledge Base.', confidence: 0.73, duration: '1.8s', status: 'review' },
];

export default function AIConsolePage() {
  const [mode, setMode] = useState<ExecutionMode>('supervised');
  const [runs, setRuns] = useState(INITIAL_RUNS);
  const [guardrails, setGuardrails] = useState({
    piiMasking: true,
    humanApproval: true,
    productionBlock: true,
  });

  const reviewCount = useMemo(() => runs.filter((run) => run.status === 'review' && !run.reviewed).length, [runs]);
  const avgConfidence = useMemo(() => Math.round((runs.reduce((sum, run) => sum + run.confidence, 0) / runs.length) * 100), [runs]);

  const selectMode = (next: ExecutionMode) => {
    setMode(next);
    toast.success(next === 'copilot' ? 'AI chỉ tạo đề xuất; kỹ thuật viên sẽ thực thi.' : 'AI được phép tự xử lý các tác vụ đã được phê duyệt policy.');
  };

  const reviewRun = (id: string, reviewed: 'helpful' | 'unsafe') => {
    setRuns((items) => items.map((item) => item.id === id ? { ...item, reviewed } : item));
    toast.success(reviewed === 'helpful' ? 'Đã lưu phản hồi tích cực cho lần đánh giá sau.' : 'Đã đánh dấu lần chạy để rà soát policy và prompt.');
  };

  return (
    <div>
      <PageHeader
        title="AI agent console"
        subtitle="Kiểm soát quyền tự động hóa, guardrails và các quyết định cần người phê duyệt."
        action={<span className="badge badge-in_progress"><span className="pulse-dot" /> Engine online</span>}
      />

      <div className="admin-console-grid">
        <section className="card admin-panel">
          <div className="admin-panel-heading">
            <span className="admin-panel-icon"><Cpu size={18} /></span>
            <div><h2>Chế độ thực thi</h2><p>Thay đổi này áp dụng cho các ticket mới.</p></div>
          </div>
          <div className="execution-mode-grid">
            <button type="button" className={`execution-mode ${mode === 'copilot' ? 'selected' : ''}`} onClick={() => selectMode('copilot')}>
              <Bot size={18} />
              <span>Copilot</span>
              <small>AI phân tích, trích nguồn và soạn phản hồi. Người dùng quyết định mọi thao tác.</small>
            </button>
            <button type="button" className={`execution-mode ${mode === 'supervised' ? 'selected' : ''}`} onClick={() => selectMode('supervised')}>
              <ShieldCheck size={18} />
              <span>Tự động có giám sát</span>
              <small>Chỉ chạy playbook rủi ro thấp; các bước production, quyền và dữ liệu nhạy cảm luôn qua HITL.</small>
            </button>
          </div>
          <div className="mode-note"><CircleAlert size={15} /> Không có chế độ “tự động hoàn toàn” cho thao tác access hoặc production.</div>
        </section>

        <aside className="card admin-panel">
          <div className="admin-panel-heading">
            <span className="admin-panel-icon"><ShieldCheck size={18} /></span>
            <div><h2>Guardrails đang áp dụng</h2><p>Chính sách được kiểm tra trước khi gọi công cụ.</p></div>
          </div>
          <div className="guardrail-list">
            {[
              ['piiMasking', 'Che dữ liệu nhạy cảm trong prompt và trace'],
              ['humanApproval', 'Bắt buộc HITL khi confidence thấp hoặc VIP'],
              ['productionBlock', 'Chặn thay đổi production ngoài change window'],
            ].map(([key, label]) => (
              <label key={key} className="guardrail-row">
                <span>{label}</span>
                <input type="checkbox" checked={guardrails[key as keyof typeof guardrails]} onChange={() => setGuardrails((current) => ({ ...current, [key]: !current[key as keyof typeof current] }))} />
              </label>
            ))}
          </div>
        </aside>
      </div>

      <div className="admin-console-stats">
        <Metric icon={Timer} label="Lần chạy hôm nay" value="128" />
        <Metric icon={CheckCircle2} label="Confidence trung bình" value={`${avgConfidence}%`} />
        <Metric icon={CircleAlert} label="Đang chờ review" value={String(reviewCount)} warning />
      </div>

      <section className="card admin-panel" style={{ marginTop: 16 }}>
        <div className="admin-panel-heading">
          <span className="admin-panel-icon"><Bot size={18} /></span>
          <div><h2>Nhật ký thực thi gần đây</h2><p>Đánh giá nhanh sẽ được đưa vào tập benchmark và luồng cải tiến prompt.</p></div>
        </div>
        <div className="agent-run-list">
          {runs.map((run) => (
            <article key={run.id} className="agent-run">
              <div className="agent-run-main">
                <div className="agent-run-meta"><span>{run.id}</span><span>{run.ticket}</span><span className={run.status === 'review' ? 'badge badge-pending_hitl' : 'badge badge-closed'}>{run.status === 'review' ? 'Cần review' : 'Đã hoàn tất'}</span></div>
                <p>{run.action}</p>
              </div>
              <div className="agent-run-score"><strong>{Math.round(run.confidence * 100)}%</strong><span>confidence · {run.duration}</span></div>
              <div className="agent-run-actions">
                <button type="button" aria-label={`Phản hồi tốt cho ${run.id}`} className={run.reviewed === 'helpful' ? 'feedback selected' : 'feedback'} onClick={() => reviewRun(run.id, 'helpful')}><ThumbsUp size={15} /></button>
                <button type="button" aria-label={`Đánh dấu rủi ro cho ${run.id}`} className={run.reviewed === 'unsafe' ? 'feedback danger selected' : 'feedback danger'} onClick={() => reviewRun(run.id, 'unsafe')}><ThumbsDown size={15} /></button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value, warning = false }: { icon: typeof Timer; label: string; value: string; warning?: boolean }) {
  return <div className="stat-card"><div className="metric-label"><span>{label}</span><Icon size={16} /></div><strong className={warning ? 'metric-warning' : ''}>{value}</strong></div>;
}
