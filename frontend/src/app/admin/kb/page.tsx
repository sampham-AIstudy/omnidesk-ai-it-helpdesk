'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { BookOpen, Edit3, Plus, RefreshCw, Save, Search, Trash2, X } from 'lucide-react';
import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import { KBEntry } from '@/types';
import { CATEGORY_LABELS, COMPANY_LABELS, getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

type KBForm = {
  title: string;
  content: string;
  solution: string;
  runbook: string;
  category: string;
  tags: string;
  company_unit: string;
  department: string;
  applicable_to_all: boolean;
};

const EMPTY_FORM: KBForm = {
  title: '',
  content: '',
  solution: '',
  runbook: '',
  category: 'software',
  tags: '',
  company_unit: '',
  department: '',
  applicable_to_all: true,
};

const CATEGORIES = Object.keys(CATEGORY_LABELS);

export default function KBPage() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState<KBEntry | null>(null);
  const [form, setForm] = useState<KBForm>(EMPTY_FORM);

  const { data: stats } = useQuery({
    queryKey: ['kb-stats'],
    queryFn: async () => (await api.get('/admin/kb/stats')).data,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['admin-kb'],
    queryFn: async () => (await api.get('/admin/kb')).data as KBEntry[],
  });

  const entries = useMemo(() => data ?? [], [data]);
  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return entries;
    return entries.filter((entry) => `${entry.title} ${entry.content} ${entry.tags ?? ''}`.toLowerCase().includes(text));
  }, [entries, query]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        solution: form.solution || null,
        runbook: form.runbook || null,
        tags: form.tags || null,
        company_unit: form.applicable_to_all ? null : form.company_unit || null,
        department: form.applicable_to_all ? null : form.department || null,
      };
      if (editing) return (await api.patch(`/admin/kb/${editing.id}`, payload)).data;
      return (await api.post('/admin/kb', payload)).data;
    },
    onSuccess: () => {
      toast.success(editing ? 'Đã cập nhật tài liệu KB' : 'Đã thêm tài liệu KB');
      queryClient.invalidateQueries({ queryKey: ['admin-kb'] });
      queryClient.invalidateQueries({ queryKey: ['kb-stats'] });
      resetForm();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (entryId: number) => (await api.delete(`/admin/kb/${entryId}`)).data,
    onSuccess: () => {
      toast.success('Đã xóa tài liệu khỏi KB');
      queryClient.invalidateQueries({ queryKey: ['admin-kb'] });
      queryClient.invalidateQueries({ queryKey: ['kb-stats'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const resetForm = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
  };

  const startEdit = (entry: KBEntry) => {
    setEditing(entry);
    setForm({
      title: entry.title,
      content: entry.content,
      solution: entry.solution ?? '',
      runbook: entry.runbook ?? '',
      category: entry.category,
      tags: entry.tags ?? '',
      company_unit: entry.company_unit ?? '',
      department: entry.department ?? '',
      applicable_to_all: entry.applicable_to_all,
    });
  };

  return (
    <div>
      <PageHeader
        title="Quản lý knowledge base"
        subtitle="Tài liệu ở đây được index vào vector DB và lọc theo phân quyền khi agent truy vấn RAG."
        action={
          <button className="btn-ghost" onClick={() => queryClient.invalidateQueries({ queryKey: ['admin-kb'] })}>
            <RefreshCw size={15} />
            Làm mới
          </button>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 410px', gap: 18, alignItems: 'start' }}>
        <section style={{ display: 'grid', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <Stat label="Vector docs" value={stats?.chroma_documents ?? 0} />
            <Stat label="KB entries" value={entries.length} />
            <Stat label="Scoped docs" value={entries.filter((entry) => !entry.applicable_to_all).length} />
          </div>

          <div className="card" style={{ padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Search size={16} color="var(--text-muted)" />
              <input
                className="input-field"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm theo tiêu đề, nội dung, tags..."
                style={{ border: 0, boxShadow: 'none', padding: 0 }}
              />
            </div>
          </div>

          <div className="card" style={{ overflow: 'hidden' }}>
            {isLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 54 }}><Spinner size={32} /></div>
            ) : filtered.length === 0 ? (
              <EmptyState icon="inbox" title="Không có tài liệu" desc="Thêm tài liệu để agent có nguồn trả lời RAG." />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tài liệu</th>
                    <th>Category</th>
                    <th>Scope</th>
                    <th>Runbook</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <div style={{ color: 'var(--text)', fontWeight: 800, marginBottom: 3 }}>{entry.title}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: 12, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{entry.content}</div>
                        {entry.tags && <div style={{ color: 'var(--cyan)', fontSize: 11, marginTop: 5 }}>{entry.tags}</div>}
                      </td>
                      <td>{CATEGORY_LABELS[entry.category as keyof typeof CATEGORY_LABELS] ?? entry.category}</td>
                      <td>
                        {entry.applicable_to_all ? (
                          <span className="badge badge-low">Toàn tập đoàn</span>
                        ) : (
                          <span className="badge badge-in_progress">
                            {COMPANY_LABELS[entry.company_unit ?? ''] ?? entry.company_unit}
                            {entry.department ? ` · ${entry.department}` : ''}
                          </span>
                        )}
                      </td>
                      <td>{entry.runbook ? <span className="badge badge-medium">Có</span> : <span className="muted">Không</span>}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          <button className="btn-ghost" style={{ width: 32, padding: 0 }} onClick={() => startEdit(entry)}><Edit3 size={14} /></button>
                          <button className="btn-ghost" style={{ width: 32, padding: 0, color: 'var(--red)' }} onClick={() => deleteMutation.mutate(entry.id)} disabled={deleteMutation.isPending}><Trash2 size={14} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <aside className="card" style={{ padding: 16, position: 'sticky', top: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookOpen size={17} color="var(--primary)" />
              <h2 className="section-title">{editing ? 'Sửa tài liệu' : 'Thêm tài liệu'}</h2>
            </div>
            {editing && <button className="btn-ghost" style={{ width: 32, padding: 0 }} onClick={resetForm}><X size={14} /></button>}
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <Field label="Tiêu đề">
              <input className="input-field" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
            </Field>
            <Field label="Nội dung">
              <textarea className="input-field" rows={5} value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} />
            </Field>
            <Field label="Giải pháp">
              <textarea className="input-field" rows={3} value={form.solution} onChange={(event) => setForm({ ...form, solution: event.target.value })} />
            </Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Field label="Category">
                <select className="input-field" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
                  {CATEGORIES.map((category) => <option key={category} value={category}>{CATEGORY_LABELS[category as keyof typeof CATEGORY_LABELS]}</option>)}
                </select>
              </Field>
              <Field label="Tags">
                <input className="input-field" value={form.tags} onChange={(event) => setForm({ ...form, tags: event.target.value })} />
              </Field>
            </div>
            <Field label="Runbook JSON">
              <textarea className="input-field" rows={3} value={form.runbook} onChange={(event) => setForm({ ...form, runbook: event.target.value })} placeholder='{"steps":["..."]}' />
            </Field>

            <button
              type="button"
              className={form.applicable_to_all ? 'btn-primary' : 'btn-ghost'}
              onClick={() => setForm({ ...form, applicable_to_all: !form.applicable_to_all })}
              style={{ justifyContent: 'flex-start' }}
            >
              {form.applicable_to_all ? 'Scope: toàn tập đoàn' : 'Scope: giới hạn'}
            </button>

            {!form.applicable_to_all && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Field label="Công ty">
                  <select className="input-field" value={form.company_unit} onChange={(event) => setForm({ ...form, company_unit: event.target.value })}>
                    <option value="">Chọn công ty</option>
                    {Object.entries(COMPANY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </Field>
                <Field label="Phòng ban">
                  <input className="input-field" value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} placeholder="VD: ICU, Finance" />
                </Field>
              </div>
            )}

            <button
              className="btn-primary"
              disabled={saveMutation.isPending || !form.title.trim() || !form.content.trim()}
              onClick={() => saveMutation.mutate()}
              style={{ height: 42 }}
            >
              {saveMutation.isPending ? <Spinner size={15} /> : editing ? <Save size={15} /> : <Plus size={15} />}
              {editing ? 'Lưu thay đổi' : 'Thêm vào KB'}
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
      <div style={{ color: 'var(--primary)', fontSize: 26, fontWeight: 800 }}>{value}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'grid', gap: 6 }}>
      <span style={{ color: 'var(--text)', fontSize: 12, fontWeight: 800 }}>{label}</span>
      {children}
    </label>
  );
}
