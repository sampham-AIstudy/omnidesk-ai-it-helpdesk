'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { 
  Search, BookOpen, ThumbsUp, ChevronRight, Eye, Tag, X, FileText, 
  CheckCircle2, Wrench, Shield, Layers, HelpCircle
} from 'lucide-react';
import { PageHeader, Spinner } from '@/components/ui';
import api from '@/lib/api';

interface KBEntry {
  id: number;
  chroma_id: string | null;
  title: string;
  content: string;
  solution: string | null;
  runbook: string | null;
  category: string;
  tags: string | null;
  company_unit: string | null;
  department: string | null;
  applicable_to_all: boolean;
  usage_count: number;
  helpful_votes: number;
  is_active: boolean;
  created_at: string;
}

export default function EndUserHelpCenterPage() {
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [votedIds, setVotedIds] = useState<Set<number>>(new Set());
  const [activeArticle, setActiveArticle] = useState<KBEntry | null>(null);

  const { data: articles = [], isLoading, isError, refetch } = useQuery<KBEntry[]>({
    queryKey: ['kb-articles'],
    queryFn: async () => (await api.get('/admin/kb')).data,
  });

  const voteMutation = useMutation({
    mutationFn: async (articleId: number) =>
      (await api.post(`/admin/kb/${articleId}/vote`)).data,
    onSuccess: (updatedArticle: KBEntry) => {
      toast.success('Cảm ơn bạn đã đánh giá bài viết hữu ích!');
      refetch();
      if (activeArticle && activeArticle.id === updatedArticle.id) {
        setActiveArticle(updatedArticle);
      }
    },
    onError: () => toast.error('Không thể lưu lượt bình chọn'),
  });

  const unvoteMutation = useMutation({
    mutationFn: async (articleId: number) =>
      (await api.post(`/admin/kb/${articleId}/unvote`)).data,
    onSuccess: (updatedArticle: KBEntry) => {
      toast.success('Đã gỡ lượt đánh giá hữu ích!');
      refetch();
      if (activeArticle && activeArticle.id === updatedArticle.id) {
        setActiveArticle(updatedArticle);
      }
    },
    onError: () => toast.error('Không thể gỡ lượt bình chọn'),
  });

  const handleVote = (e: React.MouseEvent, artId: number) => {
    e.stopPropagation();
    if (votedIds.has(artId)) {
      setVotedIds((prev) => {
        const next = new Set(prev);
        next.delete(artId);
        return next;
      });
      unvoteMutation.mutate(artId);
    } else {
      setVotedIds((prev) => new Set(prev).add(artId));
      voteMutation.mutate(artId);
    }
  };

  const categories = useMemo(() => {
    const cats = Array.from(new Set(articles.map((a) => a.category)));
    return ['ALL', ...cats];
  }, [articles]);

  const filteredArticles = useMemo(() => {
    return articles.filter((a) => {
      const matchesCategory = selectedCategory === 'ALL' || a.category === selectedCategory;
      const q = query.toLowerCase().trim();
      const matchesQuery = !q || 
        a.title.toLowerCase().includes(q) || 
        a.content.toLowerCase().includes(q) || 
        (a.solution && a.solution.toLowerCase().includes(q)) ||
        (a.tags && a.tags.toLowerCase().includes(q));
      return matchesCategory && matchesQuery;
    });
  }, [articles, selectedCategory, query]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trung Tâm Trợ Giúp Tri Thức CNTT (Help Center Knowledge Base)"
        subtitle="Tra cứu các bài viết hướng dẫn xử lý sự cố chuẩn Microsoft & Doanh nghiệp dành cho toàn thể nhân viên."
      />

      {/* SEARCH BAR & CATEGORY TABS */}
      <div className="glass-card-light rounded-3xl p-6 space-y-4 border border-slate-200">
        <div className="relative">
          <Search size={18} className="absolute left-4 top-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm kiếm bài viết hướng dẫn (ví dụ: Wi-Fi, Outlook, VPN, Mật khẩu, SAP)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white rounded-2xl border border-slate-300 text-sm font-semibold text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        {/* CATEGORY FILTER CHIPS */}
        <div className="flex flex-wrap gap-2 pt-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat === 'ALL' ? ' Tất Cả Danh Mục' : cat}
            </button>
          ))}
        </div>

        {/* ARTICLES GRID */}
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <Spinner size={28} />
            <span className="text-xs font-semibold text-slate-500">Đang tải kho tri thức CNTT...</span>
          </div>
        ) : isError ? (
          <div className="p-6 text-center text-xs font-bold text-rose-600 bg-rose-50 rounded-2xl">
            Không thể tải dữ liệu kho tri thức. Vui lòng kiểm tra lại kết nối.
          </div>
        ) : filteredArticles.length === 0 ? (
          <div className="py-12 text-center text-slate-400 space-y-2">
            <BookOpen size={36} className="mx-auto text-slate-300" />
            <div className="text-sm font-bold text-slate-600">Không tìm thấy bài viết phù hợp</div>
            <div className="text-xs">Thử tìm kiếm với từ khóa khác như "VPN", "Outlook", "Password"</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {filteredArticles.map((art) => (
              <div
                key={art.id}
                onClick={() => setActiveArticle(art)}
                className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between space-y-3 group"
              >
                <div>
                  <div className="flex items-center justify-between text-xs text-slate-400 font-semibold mb-2">
                    <span className="px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 font-bold uppercase text-[10px]">
                      {art.category}
                    </span>
                    <span className="flex items-center gap-1 text-[11px]">
                      <Eye size={12} /> {art.usage_count || 120} lượt xem
                    </span>
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm line-clamp-2 group-hover:text-blue-600 transition-colors" style={{ fontFamily: 'Outfit, sans-serif' }}>
                    {art.title}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-3 mt-2 font-medium leading-relaxed">
                    {art.content}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={(e) => handleVote(e, art.id)}
                    className={`text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                      votedIds.has(art.id) ? 'text-blue-600 font-bold' : 'text-slate-600 hover:text-blue-600'
                    }`}
                  >
                    <ThumbsUp size={13} className={votedIds.has(art.id) ? 'fill-blue-600 text-blue-600' : ''} />
                    <span>Hữu ích ({art.helpful_votes || 0})</span>
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveArticle(art);
                    }}
                    className="text-xs font-bold text-blue-600 group-hover:translate-x-1 transition-transform flex items-center gap-0.5"
                  >
                    <span>Xem chi tiết</span>
                    <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* KB ARTICLE DETAIL MODAL */}
      {activeArticle && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-2xl border border-slate-200 p-6 md:p-8 space-y-6 relative animate-in fade-in zoom-in duration-200">
            {/* CLOSE BUTTON */}
            <button
              onClick={() => setActiveArticle(null)}
              className="absolute top-5 right-5 w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center transition-colors"
            >
              <X size={18} />
            </button>

            {/* MODAL HEADER */}
            <div className="space-y-3 pr-8">
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 rounded-lg bg-blue-100 text-blue-700 font-bold uppercase text-xs">
                  {activeArticle.category}
                </span>
                <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
                  <Eye size={13} /> {activeArticle.usage_count || 120} lượt truy cập
                </span>
              </div>
              <h2 className="text-xl font-extrabold text-slate-900 leading-snug" style={{ fontFamily: 'Outfit, sans-serif' }}>
                {activeArticle.title}
              </h2>
            </div>

            {/* DESCRIPTION / CONTENT */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText size={14} className="text-blue-600" /> Mô Tả Sự Cố & Tổng Quan
              </h3>
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 text-sm text-slate-700 leading-relaxed font-medium whitespace-pre-line">
                {activeArticle.content}
              </div>
            </div>

            {/* SOLUTION STEPS */}
            {activeArticle.solution && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 size={14} className="text-emerald-600" /> Hướng Dẫn Khắc Phục Khuyên Dùng
                </h3>
                <div className="p-4 bg-emerald-50/70 rounded-2xl border border-emerald-200 text-sm text-emerald-900 leading-relaxed font-medium whitespace-pre-line">
                  {activeArticle.solution}
                </div>
              </div>
            )}

            {/* RUNBOOK STEPS IF AVAILABLE */}
            {activeArticle.runbook && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Wrench size={14} className="text-amber-600" /> Quy Trình Kỹ Thuật (Runbook)
                </h3>
                <div className="p-4 bg-amber-50/70 rounded-2xl border border-amber-200 text-xs font-mono text-amber-900 leading-relaxed whitespace-pre-line">
                  {activeArticle.runbook}
                </div>
              </div>
            )}

            {/* METADATA TAGS & SCOPE */}
            <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Tag size={13} className="text-slate-400" />
                <span className="font-semibold text-slate-500">Thẻ liên quan:</span>
                <span className="font-bold text-blue-600">{activeArticle.tags || 'General, HelpDesk'}</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-500 font-medium">
                <Shield size={13} className="text-slate-400" />
                <span>Phạm vi: {activeArticle.applicable_to_all ? 'Toàn tập đoàn' : activeArticle.company_unit || 'Nội bộ'}</span>
              </div>
            </div>

            {/* MODAL FOOTER */}
            <div className="pt-3 flex items-center justify-between">
              <button
                onClick={(e) => {
                  if (activeArticle) handleVote(e, activeArticle.id);
                }}
                className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-colors ${
                  activeArticle && votedIds.has(activeArticle.id)
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700'
                }`}
              >
                <ThumbsUp size={14} className={activeArticle && votedIds.has(activeArticle.id) ? 'fill-blue-600 text-blue-600' : ''} />
                <span>
                  Bài viết này hữu ích ({activeArticle?.helpful_votes || 0})
                </span>
              </button>

              <button
                onClick={() => setActiveArticle(null)}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs transition-colors shadow-sm"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
