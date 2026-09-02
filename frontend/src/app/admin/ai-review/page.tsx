'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ShieldCheck, X, AlertCircle } from 'lucide-react';

import { EmptyState, PageHeader, Spinner } from '@/components/ui';
import api from '@/lib/api';
import { getErrorMessage } from '@/lib/utils';

type PreferenceCandidate = {
  candidate_id: string; tenant_id: string; prompt: string; chosen: string; rejected: string;
  source_event_ids: string[]; quality_score: number; quality_tier: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence: { evidence?: string[]; ratings?: number[]; outcomes?: string[]; source_ids?: string[]; citations?: Array<{ title?: string; label?: string; source_id?: string; domain?: string }> };
};

export default function AIHumanReviewQueuePage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ['preference-candidates', 'PENDING_REVIEW'],
    queryFn: async () => (await api.get('/admin/preference-candidates', { params: { status: 'PENDING_REVIEW' } })).data as { items: PreferenceCandidate[] },
  });
  const review = useMutation({
    mutationFn: async ({ candidateId, status }: { candidateId: string; status: 'APPROVED' | 'REJECTED' }) =>
      (await api.post(`/admin/preference-candidates/${candidateId}/review`, { status })).data,
    onSuccess: () => { setFeedback({ type: 'success', message: 'Review decision saved.' }); queryClient.invalidateQueries({ queryKey: ['preference-candidates'] }); },
    onError: (error) => setFeedback({ type: 'error', message: getErrorMessage(error) }),
  });
  const candidates = data?.items ?? [];
  return <div className="space-y-6">
    <PageHeader title="Preference Review Queue" subtitle="Filtered data with exact answer provenance." />
    {feedback && (
      <div className={`flex items-center gap-2 rounded-2xl border p-4 text-sm ${feedback.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : 'border-rose-200 bg-rose-50 text-rose-950'}`}>
        <AlertCircle size={16} />
        {feedback.message}
      </div>
    )}
    <section className="flex gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950"><ShieldCheck className="mt-0.5 shrink-0 text-emerald-700" size={18} />Only approved pairs can be exported offline. This page never trains or changes a model.</section>
    {isLoading ? <div className="flex justify-center p-10"><Spinner /></div> : candidates.length === 0 ? <EmptyState title="No pending preference pairs" desc="Feedback without adequate evidence does not become a preference pair." /> : candidates.map((item) => <article key={item.candidate_id} className="glass-card-light space-y-4 rounded-3xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2"><div className="text-xs text-slate-500">Tenant: {item.tenant_id} · Score: {item.quality_score.toFixed(2)}</div><span className={`rounded-full px-3 py-1 text-xs font-bold ${item.quality_tier === 'HIGH' ? 'bg-emerald-100 text-emerald-800' : item.quality_tier === 'MEDIUM' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'}`}>{item.quality_tier}</span></div>
      <div><p className="text-xs font-bold uppercase text-slate-500">Query</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-900">{item.prompt}</p></div>
      <div className="grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border border-rose-200 bg-rose-50 p-4"><p className="text-xs font-bold uppercase text-rose-700">AI answer rejected</p><p className="mt-2 whitespace-pre-wrap text-sm text-slate-900">{item.rejected}</p></div><div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-bold uppercase text-emerald-700">Preferred answer</p><p className="mt-2 whitespace-pre-wrap text-sm text-slate-900">{item.chosen}</p></div></div>
      <p className="text-xs text-slate-600">Evidence: {(item.evidence.evidence ?? []).join(', ') || 'N/A'} · Ratings: {(item.evidence.ratings ?? []).join(', ') || 'N/A'} · Outcomes: {(item.evidence.outcomes ?? []).join(', ') || 'N/A'}</p><p className="text-xs text-slate-500">Sources: {(item.evidence.source_ids ?? item.source_event_ids).join(', ') || 'N/A'}</p>
      <p className="text-xs text-slate-500">Citations: {(item.evidence.citations ?? []).map((citation) => citation.title ?? citation.label ?? citation.source_id ?? citation.domain ?? 'source').join(', ') || 'N/A'}</p><div className="flex justify-end gap-2"><button onClick={() => review.mutate({ candidateId: item.candidate_id, status: 'REJECTED' })} disabled={review.isPending} className="inline-flex items-center gap-1 rounded-xl border border-rose-300 px-3 py-2 text-xs font-bold text-rose-700"><X size={14} /> Reject</button><button onClick={() => review.mutate({ candidateId: item.candidate_id, status: 'APPROVED' })} disabled={review.isPending} className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white"><Check size={14} /> Approve</button></div>
    </article>)}</div>;
}
