import {
  Globe,
  Mail,
  FolderOpen,
  Cloud,
  AppWindow,
  Database,
  CheckCircle2,
  Loader2,
  OctagonAlert,
  AlertTriangle,
  Wrench,
} from 'lucide-react';

export type HealthStatus =
  | 'OPERATIONAL'
  | 'DEGRADED'
  | 'PARTIAL_OUTAGE'
  | 'MAJOR_OUTAGE'
  | 'MAINTENANCE';

export type ServiceType = 'BUSINESS' | 'TECHNICAL';

export type DepKind = 'APPLICATION' | 'INFRASTRUCTURE' | 'NETWORK' | 'IDENTITY' | 'DNS';
export type DepStatus = 'OK' | 'WARN' | 'DOWN';

export interface ServiceDep {
  id: string; // e.g. "ci-vpngw-01"
  name: string;
  kind: DepKind;
  status: DepStatus;
  details?: string;
  owner?: string;
  ip?: string;
  rack?: string;
}

export interface ImpactUserRow {
  id: string;
  name: string;
  department: string;
  impactReason: string;
}

export interface ServiceItem {
  id: string;                 // "svc-vpn"
  name: string;               // "Corporate VPN"
  type: ServiceType;
  status: HealthStatus;
  ownerTeam: string;          // "Network Team"
  slaTarget: string;          // "99.95%"
  currentSla: string;         // "99.91%" (rolling 30d)
  dependencies: ServiceDep[]; // CMDB links
  openIncidents: number;      // 3
  activeChanges: number;      // 1
  problems: number;           // 1
  impactedUsers?: number;     // 2300
  impactSummary?: string;
  iconName: string;
  description: string;
  channel?: string;
  lastUpdated?: string;
  impactChain?: string[];     // ["Server X bị lỗi", "VPN Service ảnh hưởng", "2.300 employees impacted"]
  impactedDepartments?: string[];
  impactedUserList?: ImpactUserRow[];
  revenueImpactHourly?: string; // "$12.4K/giờ"
}

export const HEALTH_STATUS_META: Record<
  HealthStatus,
  {
    label: string;
    color: string;
    borderClass: string;
    bgClass: string;
    textClass: string;
    dotClass: string;
  }
> = {
  OPERATIONAL: {
    label: 'Hoạt động tốt',
    color: '#34d399',
    borderClass: 'border-emerald-400/30',
    bgClass: 'bg-emerald-400/10',
    textClass: 'text-emerald-300',
    dotClass: 'bg-emerald-400',
  },
  DEGRADED: {
    label: 'Suy giảm hiệu năng',
    color: '#fbbf24',
    borderClass: 'border-amber-400/40',
    bgClass: 'bg-amber-400/10',
    textClass: 'text-amber-300',
    dotClass: 'bg-amber-400 animate-pulse',
  },
  PARTIAL_OUTAGE: {
    label: 'Mất một phần',
    color: '#fb923c',
    borderClass: 'border-orange-400/40',
    bgClass: 'bg-orange-400/10',
    textClass: 'text-orange-300',
    dotClass: 'bg-orange-400 animate-pulse',
  },
  MAJOR_OUTAGE: {
    label: 'Mất toàn bộ',
    color: '#f87171',
    borderClass: 'border-red-400/40',
    bgClass: 'bg-red-400/10',
    textClass: 'text-red-300',
    dotClass: 'bg-red-400 animate-ping',
  },
  MAINTENANCE: {
    label: 'Bảo trì',
    color: '#60a5fa',
    borderClass: 'border-blue-400/30',
    bgClass: 'bg-blue-400/10',
    textClass: 'text-blue-300',
    dotClass: 'bg-blue-400',
  },
};

export const MOCK_SERVICES: ServiceItem[] = [
  {
    id: 'svc-vpn',
    name: 'Corporate VPN',
    type: 'BUSINESS',
    status: 'OPERATIONAL',
    ownerTeam: 'Network Team',
    slaTarget: '99.95%',
    currentSla: '99.91%',
    iconName: 'Globe',
    description: 'Dịch vụ VPN doanh nghiệp — truy cập từ xa an toàn cho toàn bộ nhân viên & phòng ban.',
    channel: 'NOC / email / Teams',
    lastUpdated: '07/08 14:02',
    impactedUsers: 2300,
    impactSummary: 'Server X lỗi → VPN Service ảnh hưởng → 2.300 employees impacted. Ước tính doanh thu ảnh hưởng: $12.4K/giờ.',
    revenueImpactHourly: '$12.4K/giờ',
    openIncidents: 3,
    activeChanges: 1,
    problems: 1,
    impactChain: ['Server X bị lỗi', 'VPN Service ảnh hưởng', '2.300 employees impacted'],
    impactedDepartments: ['Finance', 'Sales', 'HR', 'IT', 'Operations', 'Legal'],
    impactedUserList: [
      { id: 'usr-1', name: 'Nguyen Van A', department: 'Finance', impactReason: 'Không vào được VPN SSL tunnel' },
      { id: 'usr-2', name: 'Trần Thị Bích', department: 'Sales', impactReason: 'RADIUS Auth bị timeout' },
      { id: 'usr-3', name: 'Lê Minh Công', department: 'IT Department', impactReason: 'Mất kết nối JumpHost remote' },
      { id: 'usr-4', name: 'Phạm Thị Dung', department: 'Ban Giám Đốc', impactReason: 'Gián đoạn truy cập ERP từ xa' },
      { id: 'usr-5', name: 'Hoàng Văn Cường', department: 'Marketing', impactReason: 'Không mount được ổ đĩa shared' },
    ],
    dependencies: [
      {
        id: 'ci-vpngw-01',
        name: 'Palo Alto VPN Gateway',
        kind: 'INFRASTRUCTURE',
        status: 'OK',
        details: 'Palo Alto PA-3220 Cluster (PAN-OS 10.2.4)',
        owner: 'Network Team',
        ip: '10.0.4.1',
        rack: 'DC1-R12',
      },
      {
        id: 'ci-entra-id',
        name: 'Entra ID (Azure AD)',
        kind: 'IDENTITY',
        status: 'OK',
        details: 'Cloud Identity Provider & MFA',
        owner: 'Security Team',
      },
      {
        id: 'ci-dns-01',
        name: 'Internal DNS Cluster',
        kind: 'DNS',
        status: 'OK',
        details: 'Infoblox Grid 10.0.1.5',
        owner: 'Network Team',
        ip: '10.0.1.5',
        rack: 'DC1-R08',
      },
      {
        id: 'ci-igw-01',
        name: 'ISP Internet Gateway',
        kind: 'NETWORK',
        status: 'OK',
        details: 'Leased Line Viettel 1Gbps + VNPT Backup',
        owner: 'Network Team',
      },
    ],
  },
  {
    id: 'svc-m365',
    name: 'Microsoft 365',
    type: 'BUSINESS',
    status: 'DEGRADED',
    ownerTeam: 'Cloud Team',
    slaTarget: '99.90%',
    currentSla: '99.82%',
    iconName: 'Mail',
    description: 'Bộ công cụ văn phòng đám mây M365 (Exchange, Teams, SharePoint, OneDrive).',
    channel: 'Teams / Email',
    lastUpdated: '07/08 13:45',
    impactedUsers: 1200,
    impactSummary: 'Exchange Online gián đoạn latency cao → 1.200 nhân viên chậm gửi nhận email.',
    revenueImpactHourly: '$4.2K/giờ',
    openIncidents: 5,
    activeChanges: 2,
    problems: 1,
    impactChain: ['Exchange Online latency cao', 'Email chậm nhận', '1.200 employees impacted'],
    impactedDepartments: ['HR', 'Sales', 'Customer Service'],
    impactedUserList: [
      { id: 'usr-10', name: 'Đỗ Văn G', department: 'HR', impactReason: 'Email có đính kèm bị kẹt Outbox' },
      { id: 'usr-11', name: 'Trịnh Văn H', department: 'Sales', impactReason: 'Teams call bị gián đoạn thoại' },
    ],
    dependencies: [
      { id: 'ci-[#m365-exch]', name: 'Exchange Online Service', kind: 'APPLICATION', status: 'WARN', details: 'Microsoft West US Region Incident' },
      { id: 'ci-entra-id', name: 'Entra ID SSO', kind: 'IDENTITY', status: 'OK', details: 'SSO Federated Auth' },
      { id: 'ci-onedrive', name: 'OneDrive Sync Service', kind: 'APPLICATION', status: 'OK', details: 'Cloud Storage API' },
    ],
  },
  {
    id: 'svc-sap',
    name: 'ERP / SAP Core',
    type: 'BUSINESS',
    status: 'MAJOR_OUTAGE',
    ownerTeam: 'ERP Team',
    slaTarget: '99.50%',
    currentSla: '97.20%',
    iconName: 'AppWindow',
    description: 'Hệ thống quản trị doanh nghiệp SAP S/4HANA (Kế toán, Kho, Mua sắm).',
    channel: 'War Room / NOC Hotline',
    lastUpdated: '07/08 14:15',
    impactedUsers: 480,
    impactSummary: 'SAP AppServer DOWN → Ngừng toàn bộ giao dịch kho & kế toán → 480 nhân viên ngừng trệ.',
    revenueImpactHourly: '$45.0K/giờ',
    openIncidents: 1,
    activeChanges: 0,
    problems: 0,
    impactChain: ['SAN Storage multipath fail', 'SAP AppServer DOWN', '480 transactions halted'],
    impactedDepartments: ['Finance', 'Warehouse', 'Procurement'],
    impactedUserList: [
      { id: 'usr-20', name: 'Vũ Thị K', department: 'Warehouse', impactReason: 'Không xuất được phiếu kho' },
      { id: 'usr-21', name: 'Bùi Văn L', department: 'Finance', impactReason: 'SAP GUI ngắt kết nối đột ngột' },
    ],
    dependencies: [
      { id: 'ci-sap-app', name: 'SAP S/4HANA AppServer', kind: 'APPLICATION', status: 'DOWN', details: 'Linux RHEL Cluster Node 1 & 2 DOWN', ip: '192.168.20.10' },
      { id: 'ci-sap-db', name: 'HANA Database Cluster', kind: 'INFRASTRUCTURE', status: 'WARN', details: 'HANA In-Memory DB Node 1 WARN', ip: '192.168.20.12' },
      { id: 'ci-san-01', name: 'SAN Storage Array', kind: 'INFRASTRUCTURE', status: 'WARN', details: 'NetApp SAN Controller Controller B Failover' },
    ],
  },
  {
    id: 'svc-wifi',
    name: 'Corporate WiFi',
    type: 'TECHNICAL',
    status: 'OPERATIONAL',
    ownerTeam: 'Network Team',
    slaTarget: '99.90%',
    currentSla: '99.94%',
    iconName: 'Globe',
    description: 'Hạ tầng mạng không dây WPA3-Enterprise cho nhân viên & khách.',
    openIncidents: 0,
    activeChanges: 0,
    problems: 0,
    dependencies: [
      { id: 'ci-ap-ctrl', name: 'Cisco WLC Controller', kind: 'INFRASTRUCTURE', status: 'OK' },
      { id: 'ci-dns-01', name: 'Internal DNS Cluster', kind: 'DNS', status: 'OK' },
      { id: 'ci-igw-01', name: 'ISP Internet Gateway', kind: 'NETWORK', status: 'OK' },
    ],
  },
  {
    id: 'svc-findrive',
    name: 'Finance Shared Drive',
    type: 'TECHNICAL',
    status: 'DEGRADED',
    ownerTeam: 'Storage Team',
    slaTarget: '99.90%',
    currentSla: '99.65%',
    iconName: 'FolderOpen',
    description: 'Ổ đĩa chia sẻ bảo mật SMB/NFS cho khối Tài chính Kế toán.',
    openIncidents: 2,
    activeChanges: 1,
    problems: 0,
    impactedUsers: 150,
    impactSummary: 'NAS-01 iSCSI latency cao → 150 nhân viên Finance mở file Excel bị giật.',
    dependencies: [
      { id: 'ci-nas-01', name: 'Synology Enterprise NAS-01', kind: 'INFRASTRUCTURE', status: 'WARN' },
      { id: 'ci-bkup-01', name: 'Veeam Backup Repository', kind: 'INFRASTRUCTURE', status: 'DOWN' },
    ],
  },
  {
    id: 'svc-crm',
    name: 'CRM Portal',
    type: 'BUSINESS',
    status: 'MAINTENANCE',
    ownerTeam: 'Dev Team',
    slaTarget: '99.80%',
    currentSla: '99.80%',
    iconName: 'Cloud',
    description: 'Cổng thông tin quản lý quan hệ khách hàng & chăm sóc khách hàng.',
    openIncidents: 0,
    activeChanges: 1,
    problems: 0,
    dependencies: [
      { id: 'ci-web-gw', name: 'Nginx Reverse Proxy', kind: 'NETWORK', status: 'OK' },
      { id: 'ci-db-cluster', name: 'PostgreSQL DB Cluster', kind: 'INFRASTRUCTURE', status: 'OK' },
    ],
  },
];
