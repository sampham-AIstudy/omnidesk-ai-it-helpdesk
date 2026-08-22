'use client';

import React, { useState } from 'react';
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  ThumbsUp,
  X,
  Ticket,
  Wrench,
  FileText,
  Terminal,
} from 'lucide-react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Spinner } from './ui';

interface KBArticle {
  id: number;
  chroma_id?: string | null;
  title: string;
  category: string;
  content: string;
  solution?: string | null;
  runbook?: string | null;
  tags?: string | null;
  view_count?: number;
  useful_count?: number;
  helpful_votes?: number;
  created_at?: string;
}

interface AISolutionViewerProps {
  content?: string | null;
  className?: string;
}

interface SubStep {
  num: string;
  text: string;
}

interface SubBullet {
  text: string;
  isSection?: boolean;
  subSteps: SubStep[];
}

interface OrderedStep {
  num: string;
  title: string;
  bullets: SubBullet[];
}

type ParsedBlock =
  | { type: 'divider' }
  | { type: 'section_divider'; label: string }
  | { type: 'spec_tags'; tags: { label: string; value: string }[] }
  | { type: 'header'; text: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'step'; step: OrderedStep }
  | { type: 'bullet'; text: string; subSteps: SubStep[] }
  | { type: 'paragraph'; text: string };

function parseHierarchicalBlocks(text: string): ParsedBlock[] {
  if (!text) return [];

  // Remove standalone repetitive lines like "• Nguồn: [kb-002]...", "Nguồn: [web-windows-wifi-007]..."
  const cleaned = text.replace(
    /^[•\-\*]?\s*(?:Nguồn|Tham khảo|Nguồn tham khảo):\s*(?:\[[A-Za-z0-9_.:-]+\](?:\s*,\s*\[[A-Za-z0-9_.:-]+\])*)\s*$/gim,
    ''
  );

  const rawLines = cleaned.split('\n').map((l) => l.trim());
  const blocks: ParsedBlock[] = [];

  let currentStep: OrderedStep | null = null;
  let currentBullet: SubBullet | null = null;

  const flush = () => {
    if (currentStep) {
      blocks.push({ type: 'step', step: currentStep });
      currentStep = null;
      currentBullet = null;
    }
  };

  let i = 0;
  while (i < rawLines.length) {
    const line = rawLines[i];
    if (!line) {
      i++;
      continue;
    }

    // Section Divider like "--- MÔ TẢ CHI TIẾT SỰ CỐ ---"
    const sectionDividerMatch = line.match(/^(?:---+|\*\*\*+|===+)?\s*(?:---\s*)?(MÔ TẢ CHI TIẾT SỰ CỐ|MÔ TẢ SỰ CỐ|CHI TIẾT SỰ CỐ|CHI TIẾT YÊU CẦU|CHI TIẾT LỖI|MÔ TẢ LỖI)(?:\s*---)?\s*(?:---+|\*\*\*+|===+)?$/i);
    if (sectionDividerMatch) {
      flush();
      blocks.push({ type: 'section_divider', label: sectionDividerMatch[1].trim() });
      i++;
      continue;
    }

    // Bracket Spec Tags: [Key: Value]
    if (/^\[([^:\]]+):\s*([^\]]+)\]$/.test(line)) {
      flush();
      const tags: { label: string; value: string }[] = [];
      while (i < rawLines.length && /^\[([^:\]]+):\s*([^\]]+)\]$/.test(rawLines[i])) {
        const m = rawLines[i].match(/^\[([^:\]]+):\s*([^\]]+)\]$/);
        if (m) {
          tags.push({ label: m[1].trim(), value: m[2].trim() });
        }
        i++;
      }
      if (tags.length > 0) {
        blocks.push({ type: 'spec_tags', tags });
      }
      continue;
    }

    // Divider
    if (line === '---') {
      flush();
      blocks.push({ type: 'divider' });
      i++;
      continue;
    }

    // Markdown Table Detection
    if (line.startsWith('|') && line.includes('|', 1)) {
      flush();
      const tableLines: string[] = [];
      while (i < rawLines.length && rawLines[i].startsWith('|')) {
        tableLines.push(rawLines[i]);
        i++;
      }

      if (tableLines.length >= 2) {
        const parseRow = (rowStr: string) =>
          rowStr
            .split('|')
            .map((c) => c.trim())
            .filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);

        const headerCols = parseRow(tableLines[0]);
        const bodyRows: string[][] = [];

        for (let r = 1; r < tableLines.length; r++) {
          // Skip divider row e.g. |---|---|
          if (/^\|[-:\s|]+\|$/.test(tableLines[r])) continue;
          const cols = parseRow(tableLines[r]);
          if (cols.length > 0) bodyRows.push(cols);
        }

        blocks.push({ type: 'table', headers: headerCols, rows: bodyRows });
      }
      continue;
    }

    // Section Header
    if (/^(Tóm tắt hành động|Hành động tiếp theo:|Giải pháp khắc phục|Lưu ý quan trọng:|Lưu ý:)/i.test(line)) {
      flush();
      blocks.push({ type: 'header', text: line });
      i++;
      continue;
    }

    // Sub-section Alpha Headers (e.g. "A. WiFi yếu/mất kết nối liên tục", "B. ...")
    const alphaMatch = line.match(/^([A-Z])\.\s+(.*)$/);
    if (alphaMatch) {
      const letter = alphaMatch[1];
      const subTitle = alphaMatch[2];
      if (currentStep) {
        currentBullet = { text: `${letter}. ${subTitle}`, isSection: true, subSteps: [] };
        currentStep.bullets.push(currentBullet);
      } else {
        flush();
        blocks.push({ type: 'header', text: `${letter}. ${subTitle}` });
      }
      i++;
      continue;
    }

    // Numbered Item (e.g. "1. Kiểm tra..." or "1. Mở Command Prompt...")
    const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      const numStr = numMatch[1];
      const rest = numMatch[2];
      const num = parseInt(numStr, 10) || 1;
      const prevNum: number = currentStep ? parseInt(currentStep.num, 10) : 0;
      const expectedNext: number = prevNum + 1;

      // Top-level step detection (matches sequence 1, 2, 3...)
      if (
        num === expectedNext &&
        (!currentBullet || !currentBullet.text.endsWith(':') || currentBullet.subSteps.length === 0)
      ) {
        flush();
        currentStep = { num: String(num), title: rest, bullets: [] };
        currentBullet = null;
      } else if (currentBullet) {
        // Sub-numbered step indented inside current bullet
        currentBullet.subSteps.push({ num: String(num), text: rest });
      } else {
        flush();
        currentStep = { num: String(num), title: rest, bullets: [] };
        currentBullet = null;
      }
      i++;
      continue;
    }

    // Bullet Item (e.g. "• Bước 1: ...", "• Cập nhật cấu hình IP:", "- ...")
    const bulletMatch = line.match(/^[•\-\*]\s+(.*)$/);
    if (bulletMatch) {
      const bulletText = bulletMatch[1];
      currentBullet = { text: bulletText, isSection: false, subSteps: [] };
      if (currentStep) {
        currentStep.bullets.push(currentBullet);
      } else {
        blocks.push({ type: 'bullet', text: bulletText, subSteps: [] });
      }
      i++;
      continue;
    }

    // Indented command line text inside a step
    if (line.startsWith('ipconfig') || line === 'cmd' || line.startsWith('services.msc') || line.startsWith('ping ')) {
      if (currentBullet) {
        currentBullet.subSteps.push({ num: 'code', text: line });
        i++;
        continue;
      }
    }

    // Regular text (Paragraph)
    flush();
    blocks.push({ type: 'paragraph', text: line });
    i++;
  }

  flush();
  return blocks;
}

/**
 * Quick preview modal for Knowledge Base article
 */
function KBModal({ tag, onClose }: { tag: string; onClose: () => void }) {
  const { data: articles, isLoading } = useQuery<KBArticle[]>({
    queryKey: ['kb-articles-all'],
    queryFn: async () => (await api.get('/admin/kb')).data,
    staleTime: 60000,
  });

  const cleanTag = tag.replace(/[\[\]]/g, '').trim().toLowerCase(); // e.g. "kb-030" or "web-windows-wifi-007"
  const tagNum = parseInt(cleanTag.replace(/^(?:kb|web)-?/i, ''), 10);
  const tagPad = !isNaN(tagNum) ? `kb-${String(tagNum).padStart(3, '0')}` : '';

  const matched = (articles || []).find((a) => {
    const chromaLower = (a.chroma_id || '').toLowerCase();
    const titleLower = (a.title || '').toLowerCase();
    const tagLower = (a.tags || '').toLowerCase();
    return (
      chromaLower === cleanTag ||
      (tagPad !== '' && chromaLower === tagPad) ||
      chromaLower.includes(cleanTag) ||
      (!isNaN(tagNum) && a.id === tagNum) ||
      titleLower.includes(cleanTag) ||
      (tagPad !== '' && titleLower.includes(tagPad)) ||
      tagLower.includes(cleanTag)
    );
  });

  let parsedRunbookSteps: string[] = [];
  if (matched?.runbook) {
    try {
      const parsed = JSON.parse(matched.runbook);
      if (Array.isArray(parsed?.steps)) parsedRunbookSteps = parsed.steps;
    } catch {
      parsedRunbookSteps = [];
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--surface, #ffffff)',
          color: 'var(--text, #0f172a)',
          borderRadius: 16,
          maxWidth: 680,
          width: '100%',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid var(--border, #e2e8f0)',
          overflow: 'hidden',
          animation: 'fadeIn 0.15s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--surface-muted, #f8fafc)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'var(--blue-bg, #eff6ff)',
                color: '#0284c7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BookOpen size={18} />
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue, #2563eb)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Tài Liệu Tri Thức Chuẩn
              </div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text, #0f172a)' }}>
                {matched ? matched.title : `Mã tài liệu: ${cleanTag.toUpperCase()}`}
              </h3>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted, #64748b)',
              padding: 4,
              borderRadius: 6,
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: 20, overflowY: 'auto', flex: 1, display: 'grid', gap: 16 }}>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
              <Spinner size={24} />
            </div>
          ) : matched ? (
            <>
              {/* Category and Tags */}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: '#e0e7ff',
                    color: '#4338ca',
                  }}
                >
                  {matched.category.toUpperCase()}
                </span>
                {matched.chroma_id && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: '#f1f5f9',
                      color: '#475569',
                      fontFamily: 'monospace',
                    }}
                  >
                    ID: {matched.chroma_id}
                  </span>
                )}
                {matched.helpful_votes !== undefined && matched.helpful_votes > 0 && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: '#ecfdf5',
                      color: '#047857',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <ThumbsUp size={12} /> {matched.helpful_votes} hữu ích
                  </span>
                )}
              </div>

              {/* Solution / Guidance Box */}
              {matched.solution ? (
                <div
                  style={{
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: 10,
                    padding: 14,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 13, color: '#166534', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <CheckCircle2 size={16} /> Hướng dẫn khắc phục sự cố:
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.6, color: '#14532d', whiteSpace: 'pre-wrap' }}>
                    {matched.solution}
                  </div>
                </div>
              ) : null}

              {/* Content Description */}
              <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary, #334155)', whiteSpace: 'pre-wrap' }}>
                {matched.content}
              </div>

              {/* Runbook Steps if available */}
              {parsedRunbookSteps.length > 0 && (
                <div
                  style={{
                    background: 'var(--surface-muted, #f8fafc)',
                    border: '1px solid var(--border, #e2e8f0)',
                    borderRadius: 10,
                    padding: 14,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text, #0f172a)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Wrench size={16} color="var(--blue, #2563eb)" /> Quy trình kỹ thuật (Runbook):
                  </div>
                  <div style={{ display: 'grid', gap: 6 }}>
                    {parsedRunbookSteps.map((step, idx) => (
                      <div key={idx} style={{ fontSize: 12, display: 'flex', gap: 8, color: 'var(--text-secondary, #475569)' }}>
                        <span style={{ fontWeight: 700, color: 'var(--blue, #2563eb)' }}>{idx + 1}.</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted, #64748b)' }}>
              <p style={{ margin: 0, fontSize: 14 }}>Không tìm thấy bài viết chi tiết cho mã <strong>{tag}</strong> trong cơ sở dữ liệu.</p>
              <p style={{ margin: '8px 0 0 0', fontSize: 12 }}>Tài liệu này có thể thuộc tài liệu tham khảo nhanh hoặc đã được cập nhật phiên bản mới.</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--border, #e2e8f0)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'var(--surface-muted, #f8fafc)',
          }}
        >
          <span style={{ fontSize: 11, color: 'var(--text-muted, #64748b)' }}>
            OmniDesk RAG Verified Source
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              background: 'var(--blue, #2563eb)',
              color: '#ffffff',
              border: 'none',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Tokenizes text and parses Markdown formatting:
 * - Bold: `**text**`
 * - Code: `` `code` ``
 * - KB references: `[kb-001]` or `[web-windows-wifi-007]`
 * - Episodic Memory Ticket references: `[MEM-1-ticket-root]` -> Ticket #1 link
 * - Internal Ticket links: `[[ticket:1|#INC-20260816-7593]]`
 * - Markdown links: `[Label](url)`
 */
function renderInlineContent(
  text: string,
  onSelectKB: (tag: string) => void
): React.ReactNode[] {
  if (!text) return [];

  // Match all special tokens
  const regex = /(\[\[ticket:\d+\|[^\]]+\]\]|\[MEM-\d+-[^\]]+\]|\[[^\]]+\]\([^)]+\)|https?:\/\/[^\s<>)"]+|\[(?:kb|web|doc)-[A-Za-z0-9_.:-]+\]|\*\*[^*]+\*\*|`[^`]+`|\*\(Nguồn:[^)]+\)\*|SHOW PROCESSLIST|SELECT |KILL |EXPLAIN ANALYZE|ANALYZE TABLE|VACUUM ANALYZE)/gi;
  const tokens = text.split(regex);

  return tokens.map((token, idx) => {
    if (!token) return null;

    // Raw URL http:// or https://
    if (/^https?:\/\/[^\s<>)"]+$/i.test(token)) {
      return (
        <a
          key={idx}
          href={token}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--blue, #2563eb)',
            fontWeight: 700,
            textDecoration: 'underline',
            wordBreak: 'break-all',
            margin: '0 2px',
          }}
        >
          {token}
        </a>
      );
    }

    // Bold text **...**
    if (token.startsWith('**') && token.endsWith('**')) {
      return (
        <strong key={idx} style={{ fontWeight: 800, color: 'var(--text, #0f172a)' }}>
          {token.slice(2, -2)}
        </strong>
      );
    }

    // Explicit inline code `...`
    if (token.startsWith('`') && token.endsWith('`')) {
      return (
        <code
          key={idx}
          style={{
            background: 'var(--surface-muted, #f1f5f9)',
            color: 'var(--blue, #2563eb)',
            padding: '2px 6px',
            borderRadius: 4,
            fontSize: '0.9em',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontWeight: 600,
            border: '1px solid var(--border, #e2e8f0)',
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    // Episodic Memory Ticket Reference e.g. [MEM-1-ticket-root] or [MEM-4-message-10]
    const memMatch = token.match(/^\[MEM-(\d+)-[^\]]+\]$/i);
    if (memMatch) {
      const ticketId = memMatch[1];
      return (
        <Link
          key={idx}
          href={`/employee/tickets/${ticketId}`}
          title={`Xem lịch sử sự cố Ticket #${ticketId}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: '#ecfdf5',
            color: '#047857',
            padding: '2px 8px',
            borderRadius: 6,
            fontSize: '0.85em',
            fontWeight: 700,
            fontFamily: 'ui-monospace, monospace',
            border: '1px solid #a7f3d0',
            textDecoration: 'none',
            margin: '0 2px',
            transition: 'all 0.15s ease',
          }}
        >
          <Ticket size={11} />
          <span>Lịch sử Ticket #{ticketId}</span>
          <ExternalLink size={10} style={{ opacity: 0.8 }} />
        </Link>
      );
    }

    // Internal Ticket Link [[ticket:1|#INC-20260816-7593]]
    const internalTicketMatch = token.match(/^\[\[ticket:(\d+)\|([^\]]+)\]\]$/i);
    if (internalTicketMatch) {
      const ticketId = internalTicketMatch[1];
      const label = internalTicketMatch[2];
      return (
        <Link
          key={idx}
          href={`/employee/tickets/${ticketId}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: '#eff6ff',
            color: '#1d4ed8',
            padding: '2px 8px',
            borderRadius: 6,
            fontSize: '0.85em',
            fontWeight: 700,
            border: '1px solid #bfdbfe',
            textDecoration: 'none',
            margin: '0 2px',
          }}
        >
          <Ticket size={11} />
          <span>{label}</span>
        </Link>
      );
    }

    // Markdown Link [Label](url)
    const mdLinkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (mdLinkMatch) {
      const label = mdLinkMatch[1];
      const url = mdLinkMatch[2];
      return (
        <a
          key={idx}
          href={url}
          target={url.startsWith('http') ? '_blank' : '_self'}
          rel="noreferrer"
          style={{
            color: 'var(--blue, #2563eb)',
            fontWeight: 700,
            textDecoration: 'underline',
            margin: '0 2px',
          }}
        >
          {label}
        </a>
      );
    }

    // KB references [kb-xxx] or [web-xxx]
    if (/^\[(?:kb|web|doc)-[A-Za-z0-9_.:-]+\]$/i.test(token)) {
      return (
        <button
          key={idx}
          type="button"
          onClick={() => onSelectKB(token)}
          title="Bấm để xem chi tiết bài viết tri thức này"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: '#e0f2fe',
            color: '#0369a1',
            padding: '2px 8px',
            borderRadius: 6,
            fontSize: '0.85em',
            fontWeight: 700,
            fontFamily: 'ui-monospace, monospace',
            border: '1px solid #bae6fd',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            margin: '0 2px',
          }}
        >
          <BookOpen size={11} />
          {token.slice(1, -1)}
          <ExternalLink size={10} style={{ opacity: 0.8 }} />
        </button>
      );
    }

    // Common SQL commands detected automatically
    if (/^(?:SHOW PROCESSLIST|SELECT |KILL |EXPLAIN ANALYZE|ANALYZE TABLE|VACUUM ANALYZE)/i.test(token)) {
      return (
        <code
          key={idx}
          style={{
            background: '#f8fafc',
            color: '#0f172a',
            padding: '2px 5px',
            borderRadius: 4,
            fontSize: '0.88em',
            fontFamily: 'ui-monospace, Consolas, monospace',
            fontWeight: 700,
            border: '1px solid #cbd5e1',
          }}
        >
          {token}
        </code>
      );
    }

    return token;
  });
}

export function AISolutionViewer({ content, className = '' }: AISolutionViewerProps) {
  const [selectedKB, setSelectedKB] = useState<string | null>(null);

  if (!content) return null;

  const blocks = parseHierarchicalBlocks(content);

  return (
    <>
      <div
        className={`ai-solution-viewer ${className}`}
        style={{
          display: 'grid',
          gap: 12,
          fontSize: 13.5,
          lineHeight: 1.68,
          color: 'var(--text-secondary, #334155)',
        }}
      >
        {blocks.map((block, bIdx) => {
          // Divider
          if (block.type === 'divider') {
            return (
              <hr
                key={bIdx}
                style={{
                  border: 'none',
                  borderTop: '1px solid var(--border, #e2e8f0)',
                  margin: '4px 0',
                }}
              />
            );
          }

          // Section Divider (e.g. "--- MÔ TẢ CHI TIẾT SỰ CỐ ---")
          if (block.type === 'section_divider') {
            return (
              <div
                key={bIdx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  margin: '12px 0 6px',
                }}
              >
                <div style={{ height: 1, flex: 1, background: 'var(--border, #e2e8f0)' }} />
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 800,
                    color: 'var(--primary, #2563eb)',
                    background: 'var(--primary-soft, #eff6ff)',
                    border: '1px solid var(--border-subtle, #bfdbfe)',
                    padding: '3px 12px',
                    borderRadius: 20,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  {block.label}
                </span>
                <div style={{ height: 1, flex: 1, background: 'var(--border, #e2e8f0)' }} />
              </div>
            );
          }

          // Structured Spec Tags (e.g. [Hệ Thống / Dịch Vụ: ...], [Môi Trường HĐH: ...])
          if (block.type === 'spec_tags') {
            return (
              <div
                key={bIdx}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: 8,
                  padding: 10,
                  background: 'var(--surface-subtle, #f8fafc)',
                  borderRadius: 10,
                  border: '1px solid var(--border, #e2e8f0)',
                  margin: '4px 0',
                }}
              >
                {block.tags.map((tag, tIdx) => (
                  <div
                    key={tIdx}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                      padding: '6px 9px',
                      background: 'var(--surface, #ffffff)',
                      borderRadius: 6,
                      border: '1px solid var(--border-subtle, #e2e8f0)',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                    }}
                  >
                    <span style={{ fontSize: 9.5, fontWeight: 800, color: 'var(--text-muted, #64748b)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      {tag.label}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary, #0f172a)', lineHeight: 1.35 }}>
                      {tag.value}
                    </span>
                  </div>
                ))}
              </div>
            );
          }

          // Section Header
          if (block.type === 'header') {
            return (
              <div
                key={bIdx}
                style={{
                  fontWeight: 800,
                  color: 'var(--text, #0f172a)',
                  fontSize: 13.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginTop: 4,
                }}
              >
                <ChevronRight size={15} color="var(--blue, #2563eb)" />
                {renderInlineContent(block.text, setSelectedKB)}
              </div>
            );
          }

          // Markdown Table
          if (block.type === 'table') {
            return (
              <div
                key={bIdx}
                style={{
                  overflowX: 'auto',
                  margin: '6px 0',
                  borderRadius: 10,
                  border: '1px solid var(--border, #e2e8f0)',
                  background: 'var(--surface, #ffffff)',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead style={{ background: 'var(--surface-muted, #f8fafc)', borderBottom: '2px solid var(--border, #e2e8f0)' }}>
                    <tr>
                      {block.headers.map((h, hIdx) => (
                        <th key={hIdx} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 700, color: 'var(--text, #0f172a)' }}>
                          {renderInlineContent(h, setSelectedKB)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, rIdx) => (
                      <tr key={rIdx} style={{ borderBottom: '1px solid var(--border, #f1f5f9)', background: rIdx % 2 === 0 ? 'transparent' : 'rgba(241, 245, 249, 0.4)' }}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} style={{ padding: '8px 12px', color: 'var(--text-secondary, #334155)', verticalAlign: 'top' }}>
                            {renderInlineContent(cell, setSelectedKB)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          // Top-level Step with Sub-bullets & Nested Steps
          if (block.type === 'step') {
            const { num, title, bullets } = block.step;
            return (
              <div
                key={bIdx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  marginTop: 2,
                }}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'var(--blue-bg, #eff6ff)',
                    color: 'var(--blue, #2563eb)',
                    border: '1px solid #bfdbfe',
                    fontSize: 11,
                    fontWeight: 800,
                    flexShrink: 0,
                    marginTop: 1,
                  }}
                >
                  {num}
                </span>

                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, color: 'var(--text, #0f172a)', lineHeight: 1.55 }}>
                    {renderInlineContent(title, setSelectedKB)}
                  </div>

                  {bullets.length > 0 && (
                    <div style={{ display: 'grid', gap: 6, marginTop: 6, paddingLeft: 4 }}>
                      {bullets.map((b, bulletIdx) => {
                        if (b.isSection) {
                          return (
                            <div key={bulletIdx} style={{ marginTop: 6, marginBottom: 2 }}>
                              <div
                                style={{
                                  fontWeight: 800,
                                  color: 'var(--text, #0f172a)',
                                  fontSize: 13,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 6,
                                  background: 'var(--surface-muted, #f1f5f9)',
                                  border: '1px solid var(--border, #e2e8f0)',
                                  padding: '3px 8px',
                                  borderRadius: 6,
                                }}
                              >
                                {renderInlineContent(b.text, setSelectedKB)}
                              </div>
                            </div>
                          );
                        }

                        return (
                          <div key={bulletIdx} style={{ display: 'grid', gap: 4 }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, color: 'var(--text-secondary, #475569)' }}>
                              <span style={{ color: 'var(--blue, #2563eb)', lineHeight: 1.5, flexShrink: 0 }}>•</span>
                              <div style={{ flex: 1, fontWeight: b.text.endsWith(':') ? 700 : 400, color: b.text.endsWith(':') ? 'var(--text, #0f172a)' : 'inherit' }}>
                                {renderInlineContent(b.text, setSelectedKB)}
                              </div>
                            </div>

                            {/* Nested Ordered Sub-steps / Commands */}
                            {b.subSteps && b.subSteps.length > 0 && (
                              <div
                                style={{
                                  display: 'grid',
                                  gap: 4,
                                  marginTop: 3,
                                  marginBottom: 4,
                                  paddingLeft: 16,
                                  borderLeft: '2px solid #e2e8f0',
                                  marginLeft: 8,
                                }}
                              >
                                {b.subSteps.map((sub, sIdx) => {
                                  if (sub.num === 'code') {
                                    return (
                                      <div key={sIdx} style={{ margin: '1px 0' }}>
                                        <code
                                          style={{
                                            background: '#0f172a',
                                            color: '#38bdf8',
                                            padding: '2px 8px',
                                            borderRadius: 5,
                                            fontSize: 12,
                                            fontFamily: 'ui-monospace, Consolas, monospace',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: 5,
                                          }}
                                        >
                                          <Terminal size={11} /> {sub.text}
                                        </code>
                                      </div>
                                    );
                                  }

                                  return (
                                    <div key={sIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 13, color: 'var(--text-secondary, #475569)' }}>
                                      <span style={{ fontWeight: 700, color: 'var(--blue, #2563eb)', flexShrink: 0 }}>
                                        {sub.num}.
                                      </span>
                                      <div style={{ flex: 1 }}>
                                        {renderInlineContent(sub.text, setSelectedKB)}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          }

          // Top-level standalone bullet
          if (block.type === 'bullet') {
            return (
              <div key={bIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, paddingLeft: 6 }}>
                <span style={{ color: 'var(--blue, #2563eb)', lineHeight: 1.5, flexShrink: 0 }}>•</span>
                <div style={{ flex: 1 }}>{renderInlineContent(block.text, setSelectedKB)}</div>
              </div>
            );
          }

          // Regular paragraph
          return (
            <p key={bIdx} style={{ margin: 0, overflowWrap: 'anywhere' }}>
              {renderInlineContent(block.text, setSelectedKB)}
            </p>
          );
        })}
      </div>

      {/* KB Detail Modal */}
      {selectedKB && <KBModal tag={selectedKB} onClose={() => setSelectedKB(null)} />}
    </>
  );
}

export default AISolutionViewer;
