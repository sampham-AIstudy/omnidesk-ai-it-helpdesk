export interface HITLItem {
  id: string;                 // "INC-10821"
  category: string;           // "Network"
  categoryConfidence: number; // 0.61
  alternativeCategory: string;// "Security"
  altConfidence: number;      // 0.34
  proposedAction: {
    routeTeam: string;
    priority: string;
    sendKb: string;
  };
  hitlReason: string;         // "⚠ Confidence < 0.70"
  requester: string;
  summary: string;
  createdAt: string;
}

export interface TraceStep {
  name: string;
  latencyMs: number;
  status: 'SUCCESS' | 'WARN' | 'FAIL';
  details?: string;
}

export interface AITraceDetail {
  id: string; // "tr-8821"
  ticketId: string;
  totalLatencyMs: number;
  tokensUsed: number;
  costEstimate: string;
  model: string;
  promptVersion: string;
  confidence: number;
  guardrailResult: string;
  retrievedChunks: { id: string; score: number }[];
  toolCalls: string[];
  finalDecision: string;
  steps: TraceStep[];
}

export const MOCK_HITL_QUEUE: HITLItem[] = [
  {
    id: 'INC-10821',
    category: 'Network',
    categoryConfidence: 0.61,
    alternativeCategory: 'Security',
    altConfidence: 0.34,
    proposedAction: {
      routeTeam: 'Network Team',
      priority: 'P2',
      sendKb: 'KB-1021',
    },
    hitlReason: '⚠ Confidence < 0.70',
    requester: 'Nguyen Van A',
    summary: 'Không thể truy cập ổ đĩa shared nội bộ sau khi đổi mật khẩu VPN.',
    createdAt: '14:02:11',
  },
  {
    id: 'INC-10825',
    category: 'Hardware',
    categoryConfidence: 0.68,
    alternativeCategory: 'Software',
    altConfidence: 0.28,
    proposedAction: {
      routeTeam: 'Desktop Support',
      priority: 'P3',
      sendKb: 'KB-0044',
    },
    hitlReason: '⚠ Confidence < 0.70',
    requester: 'Trần Thị Bích',
    summary: 'Màn hình laptop bị sọc ngang chớp tắt khi cắm sạc.',
    createdAt: '14:10:05',
  },
];

export const MOCK_TRACE_DETAIL: AITraceDetail = {
  id: 'tr-8821',
  ticketId: 'INC-10821',
  totalLatencyMs: 2212,
  tokensUsed: 1420,
  costEstimate: '$0.0028',
  model: 'Gemini 1.5 Pro / GPT-4o',
  promptVersion: 'v2.4.1-enterprise',
  confidence: 0.61,
  guardrailResult: 'PASS (No Prompt Injection & PII Masked)',
  retrievedChunks: [
    { id: 'KB-1021', score: 0.94 },
    { id: 'KB-0821', score: 0.81 },
  ],
  toolCalls: ['query_cmdb_deps', 'check_oncall_schedule'],
  finalDecision: 'Routed to Network Team with Priority P2 & Sent KB-1021',
  steps: [
    { name: 'Request Ingestion', latencyMs: 4, status: 'SUCCESS' },
    { name: 'Input Guardrail Check', latencyMs: 21, status: 'SUCCESS' },
    { name: 'PII Detection & Masking', latencyMs: 85, status: 'SUCCESS' },
    { name: 'Classifier Model', latencyMs: 122, status: 'WARN', details: 'Confidence 61% below threshold 70%' },
    { name: 'Embedding Generation', latencyMs: 46, status: 'SUCCESS' },
    { name: 'Hybrid Search (Dense+BM25)', latencyMs: 89, status: 'SUCCESS' },
    { name: 'Cross-Encoder Reranker', latencyMs: 1800, status: 'SUCCESS' },
    { name: 'HITL Review Triggered', latencyMs: 45, status: 'WARN', details: 'Queued to Human Reviewer' },
  ],
};
