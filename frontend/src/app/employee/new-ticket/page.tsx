'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'react-hot-toast';
import { AlertTriangle, Bot, CheckCircle2, Database, GitBranch, Send, ShieldAlert } from 'lucide-react';
import AIProcessingModal from '@/components/AIProcessingModal';
import { PageHeader, Spinner } from '@/components/ui';
import { getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

const EXAMPLES = [
  {
    title: 'Không đăng nhập được VPN',
    description: 'Tôi không đăng nhập được VPN FortiClient từ sáng nay. Thông báo lỗi Authentication failed. Đã restart máy nhưng vẫn không được.',
  },
  {
    title: 'Outlook không nhận email ngoài',
    description: 'Từ hôm qua Outlook không nhận được email từ bên ngoài. Email nội bộ vẫn bình thường. Đã kiểm tra Spam nhưng không thấy.',
  },
  {
    title: 'SAP không đăng nhập được',
    description: 'Nhân viên kế toán không vào được SAP ERP, báo lỗi Maximum sessions exceeded từ 8h sáng, ảnh hưởng chốt số liệu tháng.',
  },
];

export default function NewTicketPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isProd, setIsProd] = useState(false);
  const [createdTicketNumber, setCreatedTicketNumber] = useState<string | null>(null);

  const quality = useMemo(() => {
    let score = 0;
    if (title.trim().length >= 8) score += 1;
    if (description.trim().length >= 40) score += 1;
    if (/lỗi|error|không|failed|treo|chậm|sập|vpn|email|sap/i.test(description)) score += 1;
    return score;
  }, [title, description]);

  const submitMutation = useMutation({
    mutationFn: async () => (await api.post('/tickets', {
      title: title.trim(),
      description: description.trim(),
      is_production_impact: isProd,
    })).data,
    onSuccess: (data) => setCreatedTicketNumber(data.ticket_number),
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleModalComplete = () => {
    toast.success(`Ticket ${createdTicketNumber} đã được tạo`);
    queryClient.invalidateQueries({ queryKey: ['my-tickets'] });
    router.push('/employee/tickets');
  };

  return (
    <div>
      <PageHeader
        title="Gửi ticket IT"
        subtitle="Mô tả vấn đề một lần. Agent sẽ phân loại, tìm KB, kiểm tra HITL và định tuyến."
      />

      <div className="form-aside-grid">
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'grid', gap: 16 }}>
            <div>
              <label style={{ display: 'block', color: 'var(--text)', fontSize: 13, fontWeight: 800, marginBottom: 7 }}>
                Tiêu đề
              </label>
              <input
                className="input-field"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ví dụ: Không đăng nhập được VPN"
                maxLength={200}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: 'var(--text)', fontSize: 13, fontWeight: 800, marginBottom: 7 }}>
                Mô tả chi tiết
              </label>
              <textarea
                className="input-field"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Triệu chứng, thông báo lỗi, thời điểm bắt đầu, bạn đã thử gì, tác động đến công việc..."
                rows={9}
              />
            </div>

            <button
              type="button"
              onClick={() => setIsProd((value) => !value)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: 14,
                borderRadius: 8,
                border: `1px solid ${isProd ? '#ffd4d4' : 'var(--border)'}`,
                background: isProd ? 'var(--red-soft)' : 'var(--surface-soft)',
                textAlign: 'left',
                cursor: 'pointer',
              }}
            >
              <div style={{ width: 38, height: 22, borderRadius: 999, background: isProd ? 'var(--red)' : '#cbd5e1', padding: 3 }}>
                <div style={{ width: 16, height: 16, borderRadius: 999, background: '#ffffff', transform: isProd ? 'translateX(16px)' : 'translateX(0)', transition: 'transform 0.15s ease' }} />
              </div>
              <div>
                <div style={{ color: isProd ? 'var(--red)' : 'var(--text)', fontSize: 13, fontWeight: 800 }}>Ảnh hưởng production</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Bật khi hệ thống thật, dữ liệu khách hàng, y tế, tài chính hoặc vận hành bị ảnh hưởng.</div>
              </div>
            </button>

            <button
              className="btn-primary"
              disabled={!title.trim() || !description.trim() || submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
              style={{ height: 42, width: '100%' }}
            >
              {submitMutation.isPending ? <Spinner size={16} /> : <Send size={16} />}
              Gửi và kích hoạt agent
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gap: 14 }}>
          <div className="card" style={{ padding: 16 }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 12 }}>Chất lượng mô tả</div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
              {[0, 1, 2].map((step) => (
                <div key={step} style={{ flex: 1, height: 7, borderRadius: 999, background: step < quality ? 'var(--green)' : '#e5e7eb' }} />
              ))}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.5 }}>
              {quality >= 3 ? 'Đủ thông tin để agent phân loại tốt.' : 'Thêm thông báo lỗi, thời điểm bắt đầu và tác động công việc để tăng độ chính xác.'}
            </div>
          </div>

          <div className="card" style={{ padding: 16 }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 12 }}>Agent sẽ làm gì</div>
            {[
              { icon: Bot, title: 'Classify', text: 'Category, priority, urgency, confidence.' },
              { icon: Database, title: 'RAG', text: 'Tìm bài KB đúng quyền công ty/phòng ban.' },
              { icon: ShieldAlert, title: 'HITL', text: 'Chặn tự động với production, VIP, security hoặc low confidence.' },
              { icon: GitBranch, title: 'Route', text: 'Đưa ticket tới đúng nhóm kỹ thuật.' },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} style={{ display: 'flex', gap: 10, padding: '9px 0', borderBottom: '1px solid var(--border)' }}>
                  <Icon size={17} color="var(--primary)" />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 800 }}>{item.title}</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{item.text}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <AlertTriangle size={16} color="var(--amber)" />
              <div style={{ fontSize: 13, fontWeight: 800 }}>Mẫu nhanh</div>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {EXAMPLES.map((example) => (
                <button
                  key={example.title}
                  className="btn-ghost"
                  style={{ justifyContent: 'flex-start', height: 'auto', padding: 10, textAlign: 'left' }}
                  onClick={() => {
                    setTitle(example.title);
                    setDescription(example.description);
                  }}
                >
                  <CheckCircle2 size={14} />
                  {example.title}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {createdTicketNumber && <AIProcessingModal ticketNumber={createdTicketNumber} onComplete={handleModalComplete} />}
    </div>
  );
}
