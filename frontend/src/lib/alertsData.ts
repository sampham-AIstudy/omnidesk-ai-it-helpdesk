import {
  Bell,
  BellOff,
  CheckCircle2,
  AlertOctagon,
  ShieldAlert,
  Info,
  Siren,
  Globe,
} from 'lucide-react';

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'SUPPRESSED' | 'CONVERTED';

export interface AlertItem {
  id: string;                    // e.g. "ALT-8842"
  severity: AlertSeverity;
  source: string;                // e.g. "VPN-GW-01"
  message: string;               // e.g. "VPN-GW-01 unreachable"
  metric: string;                // e.g. "ICMP ping fail ×5"
  firstSeen: string;             // e.g. "06/08 14:02:11"
  startTimestampMs: number;      // timestamp for elapsed time ticking
  duration: string;              // "00:42" elapsed
  status: AlertStatus;
  assignee?: string;
  correlationGroup?: string;     // id of AI correlation cluster e.g. "CLUSTER-VPN-01"
  convertedTicketId?: string;    // e.g. "INC-10582"
  suppressReason?: string;
  suppressUntil?: string;
}

export interface CorrelationCluster {
  id: string;
  serviceName: string;
  summary: string;
  description: string;
  alertIds: string[];
  confidencePct: number;
  aiNarrative: string;
}

export const SEVERITY_META: Record<
  AlertSeverity,
  {
    label: string;
    color: string;
    borderClass: string;
    bgClass: string;
    textClass: string;
    dotClass: string;
    cardBorder: string;
    cardBg: string;
  }
> = {
  CRITICAL: {
    label: 'CRITICAL',
    color: '#f87171',
    borderClass: 'border-red-400/40',
    bgClass: 'bg-red-400/10',
    textClass: 'text-red-300',
    dotClass: 'bg-red-400 animate-ping',
    cardBorder: 'border-red-400/30',
    cardBg: 'bg-red-400/[0.04]',
  },
  HIGH: {
    label: 'HIGH',
    color: '#fb923c',
    borderClass: 'border-orange-400/30',
    bgClass: 'bg-orange-400/10',
    textClass: 'text-orange-300',
    dotClass: 'bg-orange-400',
    cardBorder: 'border-white/10',
    cardBg: 'bg-white/[0.03]',
  },
  MEDIUM: {
    label: 'MEDIUM',
    color: '#fbbf24',
    borderClass: 'border-amber-400/30',
    bgClass: 'bg-amber-400/10',
    textClass: 'text-amber-300',
    dotClass: 'bg-amber-400',
    cardBorder: 'border-white/10',
    cardBg: 'bg-white/[0.03]',
  },
  INFO: {
    label: 'INFO',
    color: '#22d3ee',
    borderClass: 'border-cyan-400/30',
    bgClass: 'bg-cyan-400/10',
    textClass: 'text-cyan-300',
    dotClass: 'bg-cyan-400',
    cardBorder: 'border-white/10',
    cardBg: 'bg-white/[0.03]',
  },
};

export const STATUS_META: Record<
  AlertStatus,
  {
    label: string;
    borderClass: string;
    bgClass: string;
    textClass: string;
  }
> = {
  ACTIVE: {
    label: 'Hoạt động',
    borderClass: 'border-red-400/30',
    bgClass: 'bg-red-400/10',
    textClass: 'text-red-300',
  },
  ACKNOWLEDGED: {
    label: 'Đã xác nhận',
    borderClass: 'border-zinc-500/30',
    bgClass: 'bg-zinc-500/10',
    textClass: 'text-zinc-300',
  },
  SUPPRESSED: {
    label: 'Đã tắt tiếng',
    borderClass: 'border-zinc-600/30',
    bgClass: 'bg-zinc-600/10',
    textClass: 'text-zinc-400',
  },
  CONVERTED: {
    label: 'Đã chuyển Incident',
    borderClass: 'border-emerald-400/30',
    bgClass: 'bg-emerald-400/10',
    textClass: 'text-emerald-300',
  },
};

export function formatElapsedTime(startTimestampMs: number): string {
  const diffSec = Math.max(0, Math.floor((Date.now() - startTimestampMs) / 1000));
  const hours = Math.floor(diffSec / 3600);
  const mins = Math.floor((diffSec % 3600) / 60);
  const secs = diffSec % 60;

  const pad = (n: number) => n.toString().padStart(2, '0');
  if (hours > 0) {
    return `${hours}:${pad(mins)}:${pad(secs)}`;
  }
  return `${pad(mins)}:${pad(secs)}`;
}

const NOW = Date.now();

export const MOCK_ALERTS: AlertItem[] = [
  // CRITICAL ALERTS
  {
    id: 'ALT-8842',
    severity: 'CRITICAL',
    source: 'VPN-GW-01',
    message: 'VPN-GW-01 unreachable',
    metric: 'ICMP ping fail ×5 · Gateway 10.0.4.1',
    firstSeen: '06/08 14:02:11',
    startTimestampMs: NOW - 42 * 1000,
    duration: '00:42',
    status: 'ACTIVE',
    correlationGroup: 'CLUSTER-VPN-01',
  },
  {
    id: 'ALT-8843',
    severity: 'CRITICAL',
    source: 'NPS Auth',
    message: 'Authentication error rate > 35%',
    metric: 'NPS: 412/1160 fails · 5 min window',
    firstSeen: '06/08 14:01:32',
    startTimestampMs: NOW - 81 * 1000,
    duration: '01:21',
    status: 'ACTIVE',
    correlationGroup: 'CLUSTER-VPN-01',
  },
  {
    id: 'ALT-8844',
    severity: 'CRITICAL',
    source: 'EXCH-01',
    message: 'Exchange latency > 5000ms',
    metric: 'Mailbox RPC latency avg 5.8s',
    firstSeen: '06/08 13:59:41',
    startTimestampMs: NOW - 192 * 1000,
    duration: '03:12',
    status: 'ACTIVE',
    correlationGroup: 'CLUSTER-VPN-01',
  },

  // HIGH ALERTS
  {
    id: 'ALT-8838',
    severity: 'HIGH',
    source: 'BKUP-01',
    message: 'Backup job failed',
    metric: 'Full backup exit code 2 · retry in 30m',
    firstSeen: '06/08 13:50:00',
    startTimestampMs: NOW - 764 * 1000,
    duration: '12:44',
    status: 'ACKNOWLEDGED',
    assignee: 'Lê Minh Công',
  },
  {
    id: 'ALT-8835',
    severity: 'HIGH',
    source: 'FW-EDGE-02',
    message: 'Session table count > 85%',
    metric: 'Active sessions: 852,100 / 1,000,000',
    firstSeen: '06/08 13:45:10',
    startTimestampMs: NOW - 1020 * 1000,
    duration: '17:00',
    status: 'ACTIVE',
  },

  // MEDIUM ALERTS
  {
    id: 'ALT-8831',
    severity: 'MEDIUM',
    source: 'SRV-APP-04',
    message: 'CPU > 90% sustained',
    metric: 'avg 94% · 15 min window',
    firstSeen: '06/08 13:31:00',
    startTimestampMs: NOW - 1862 * 1000,
    duration: '31:02',
    status: 'ACTIVE',
  },

  // INFO ALERTS
  {
    id: 'ALT-8825',
    severity: 'INFO',
    source: 'DNS-01',
    message: 'Zone transfer retry',
    metric: 'dns.vn retry 1/3',
    firstSeen: '06/08 12:01:00',
    startTimestampMs: NOW - 7262 * 1000,
    duration: '02:01:02',
    status: 'ACKNOWLEDGED',
    assignee: 'System Admin',
  },
];

export const MOCK_CORRELATION_CLUSTER: CorrelationCluster = {
  id: 'CLUSTER-VPN-01',
  serviceName: 'Corporate VPN',
  summary: '12 alerts appear related',
  description:
    '3 alert CRITICAL cùng cụm hạ tầng VPN (Gateway, NPS auth, edge) — khả năng cao là một sự cố hạ tầng chung, chưa phải sự cố đơn lẻ.',
  alertIds: ['ALT-8842', 'ALT-8843', 'ALT-8844'],
  confidencePct: 94,
  aiNarrative:
    'Cụm 12 alert khởi phát cùng lúc 14:02. Mẫu phù hợp nhất: VPN gateway mất kết nối WAN → xác thực NPS thất bại hàng loạt → Exchange chậm do tunnel phụ tải. Đề xuất tạo 1 Major Incident thay vì 12 incident lẻ.',
};
