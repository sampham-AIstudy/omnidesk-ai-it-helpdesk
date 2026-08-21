'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  BarChart3,
  CircleDollarSign,
  RefreshCw,
  ServerCrash,
  Zap,
} from 'lucide-react';
import api from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface UserBreakdown {
  user_id: number | null;
  username: string | null;
  email: string | null;
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
}

interface ModelBreakdown {
  model_name: string;
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
}

interface TokenUsageMetrics {
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  user_breakdown: UserBreakdown[];
  model_breakdown: ModelBreakdown[];
}

// ─── Helper utils ─────────────────────────────────────────────────────────────

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatCost(usd: number): string {
  if (usd === 0) return '$0.0000';
  if (usd < 0.0001) return `< $0.0001`;
  return `$${usd.toFixed(4)}`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  accent: string;
}) {
  return (
    <div className="glass-card-light rounded-3xl border border-slate-200 p-6 flex gap-4 items-start">
      <div className={`rounded-2xl p-3 ${accent}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function TokenUsagePage() {
  const [data, setData] = useState<TokenUsageMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<TokenUsageMetrics>('/admin/token-usage');
      setData(res.data);
      setLastRefreshed(new Date());
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Không thể tải dữ liệu token usage.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Token &amp; Cost Tracking</h1>
          <p className="mt-1 text-sm text-slate-500">
            Chi phí sử dụng Mistral AI API — dữ liệu được ghi tại thời điểm gọi API
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefreshed && (
            <span className="hidden text-xs text-slate-400 sm:block">
              Cập nhật lúc {lastRefreshed.toLocaleTimeString('vi-VN')}
            </span>
          )}
          <button
            id="btn-refresh-token-usage"
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Đang tải...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <ServerCrash size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Summary metric cards */}
      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              icon={CircleDollarSign}
              label="Tổng chi phí ước tính"
              value={formatCost(data.total_cost_usd)}
              sub="USD, tính tại thời điểm gọi API"
              accent="bg-emerald-500"
            />
            <StatCard
              icon={BarChart3}
              label="Tổng lượt gọi API"
              value={data.total_requests.toLocaleString()}
              sub="Mỗi lượt = 1 llm.ainvoke()"
              accent="bg-indigo-500"
            />
            <StatCard
              icon={Zap}
              label="Prompt Tokens"
              value={formatTokens(data.total_prompt_tokens)}
              sub="Input tokens (người dùng + system)"
              accent="bg-sky-500"
            />
            <StatCard
              icon={Zap}
              label="Completion Tokens"
              value={formatTokens(data.total_completion_tokens)}
              sub="Output tokens (phản hồi AI)"
              accent="bg-violet-500"
            />
          </div>

          {/* Per-model breakdown */}
          {data.model_breakdown.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Theo Model
              </h2>
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-100 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3 text-left">Model</th>
                      <th className="px-5 py-3 text-right">Lượt gọi</th>
                      <th className="px-5 py-3 text-right">Prompt tokens</th>
                      <th className="px-5 py-3 text-right">Completion tokens</th>
                      <th className="px-5 py-3 text-right">Chi phí (USD)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.model_breakdown.map((row) => (
                      <tr key={row.model_name} className="transition hover:bg-slate-50">
                        <td className="px-5 py-3 font-medium text-slate-800">{row.model_name}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{row.total_requests.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{formatTokens(row.total_prompt_tokens)}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{formatTokens(row.total_completion_tokens)}</td>
                        <td className="px-5 py-3 text-right font-semibold text-emerald-700">{formatCost(row.total_cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Per-user breakdown */}
          {data.user_breakdown.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Theo Người Dùng
              </h2>
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <table className="w-full text-sm">
                  <thead className="border-b border-slate-100 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3 text-left">Người dùng</th>
                      <th className="px-5 py-3 text-left">Email</th>
                      <th className="px-5 py-3 text-right">Lượt gọi</th>
                      <th className="px-5 py-3 text-right">Prompt tokens</th>
                      <th className="px-5 py-3 text-right">Completion tokens</th>
                      <th className="px-5 py-3 text-right">Chi phí (USD)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.user_breakdown.map((row, idx) => (
                      <tr key={row.user_id ?? idx} className="transition hover:bg-slate-50">
                        <td className="px-5 py-3 font-medium text-slate-800">
                          {row.username ?? <span className="italic text-slate-400">system / unknown</span>}
                        </td>
                        <td className="px-5 py-3 text-slate-500">{row.email ?? '—'}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{row.total_requests.toLocaleString()}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{formatTokens(row.total_prompt_tokens)}</td>
                        <td className="px-5 py-3 text-right text-slate-600">{formatTokens(row.total_completion_tokens)}</td>
                        <td className="px-5 py-3 text-right font-semibold text-emerald-700">{formatCost(row.total_cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Empty state */}
          {data.total_requests === 0 && (
            <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-slate-300 bg-slate-50 py-16 text-center">
              <BarChart3 size={36} className="text-slate-300" />
              <p className="text-sm font-medium text-slate-500">Chưa có dữ liệu token usage</p>
              <p className="text-xs text-slate-400">
                Dữ liệu sẽ xuất hiện sau khi người dùng thực hiện các lượt gọi AI Chat hoặc AI Classifier.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
