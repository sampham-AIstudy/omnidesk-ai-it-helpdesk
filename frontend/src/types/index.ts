// TypeScript types matching backend Pydantic schemas

export type UserRole = 'employee' | 'technician' | 'manager' | 'admin';
export type CompanyUnit = 'real_estate' | 'automotive' | 'healthcare' | 'corporate';

export type TicketCategory =
  | 'network' | 'software' | 'hardware' | 'access_permission'
  | 'email' | 'erp_sap' | 'security' | 'hr_system' | 'infrastructure' | 'other';

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';
export type TicketUrgency  = 'low' | 'medium' | 'high' | 'emergency';
export type TicketStatus =
  | 'open' | 'classifying' | 'pending_hitl' | 'in_progress'
  | 'pending_closure' | 'resolved' | 'closed' | 'escalated' | 'rejected';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  company_unit: CompanyUnit;
  department: string | null;
  is_vip: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Ticket {
  id: number;
  ticket_number: string;
  title: string;
  description: string;
  category: TicketCategory | null;
  priority: TicketPriority | null;
  urgency: TicketUrgency | null;
  confidence_score: number | null;
  suggested_solution: string | null;
  rag_sources: string | null;
  agent_reasoning: string | null;
  routing_target: string | null;
  is_production_impact: boolean;
  status: TicketStatus;
  hitl_required: boolean;
  hitl_note: string | null;
  hitl_decided_at: string | null;
  submitter_id: number;
  assignee_id: number | null;
  sla_deadline: string | null;
  sla_warning_sent: boolean;
  sla_escalated: boolean;
  first_response_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgentProcessResponse {
  ticket_id: number;
  ticket_number: string;
  status: TicketStatus;
  category: TicketCategory | null;
  priority: TicketPriority | null;
  confidence_score: number | null;
  suggested_solution: string | null;
  hitl_required: boolean;
  action_taken: string;
  message: string;
}

export interface AuditLog {
  id: number;
  ticket_id: number | null;
  actor_id: number | null;
  actor_type: string;
  action: string;
  description: string;
  metadata_json: string | null;
  confidence_score: number | null;
  model_used: string | null;
  created_at: string;
}

export interface ClassificationMetrics {
  total_tickets: number;
  auto_classified: number;
  hitl_triggered: number;
  auto_closed: number;
  accuracy: number | null;
  f1_score: number | null;
  avg_confidence: number | null;
  low_confidence_rate: number | null;
}

export interface SLAMetrics {
  total_tickets: number;
  within_sla: number;
  sla_breached: number;
  escalated: number;
  avg_resolution_hours: number | null;
  sla_compliance_rate: number | null;
}

export interface DashboardResponse {
  classification: ClassificationMetrics;
  sla: SLAMetrics;
  recent_tickets: Ticket[];
  pending_hitl: Ticket[];
}

export interface KBEntry {
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
