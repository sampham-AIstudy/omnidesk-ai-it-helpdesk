export interface InfraComponent {
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  details?: string;
}

export interface OperationsJob {
  id: string;
  name: string;
  type: 'Email ingestion' | 'SLA worker' | 'RAG indexing' | 'Escalation worker' | 'Webhook deliveries' | 'AI async jobs';
  lastRun: string;
  status: 'SUCCESS' | 'RUNNING' | 'FAILED';
  queueDepth: number;
}

export const MOCK_INFRA_COMPONENTS: InfraComponent[] = [
  { name: 'API Gateway', status: 'HEALTHY' },
  { name: 'PostgreSQL Database', status: 'HEALTHY' },
  { name: 'Redis Cache', status: 'HEALTHY' },
  { name: 'Vector DB (ChromaDB)', status: 'HEALTHY' },
  { name: 'LLM Provider (Gemini/OpenAI)', status: 'DEGRADED', details: 'p95 latency spike' },
  { name: 'Embedding Engine', status: 'HEALTHY' },
  { name: 'Email Gateway (SMTP/IMAP)', status: 'HEALTHY' },
  { name: 'Background Workers', status: 'HEALTHY', details: '8/8 Active' },
];

export const MOCK_OPERATIONS_JOBS: OperationsJob[] = [
  { id: 'job-1', name: 'Email Ingestion Worker', type: 'Email ingestion', lastRun: '1 phút trước', status: 'SUCCESS', queueDepth: 0 },
  { id: 'job-2', name: 'SLA Breach Monitor Worker', type: 'SLA worker', lastRun: '30 giây trước', status: 'RUNNING', queueDepth: 23 },
  { id: 'job-3', name: 'RAG Knowledge Re-indexing', type: 'RAG indexing', lastRun: '5 phút trước', status: 'SUCCESS', queueDepth: 0 },
  { id: 'job-4', name: 'On-Call Escalation Engine', type: 'Escalation worker', lastRun: '15 giây trước', status: 'SUCCESS', queueDepth: 0 },
];
