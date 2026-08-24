export interface CINode {
  id: string;             // e.g. "ci-vpngw-01"
  name: string;           // e.g. "VPN-GW-01"
  kind: 'INTERNET' | 'LOAD_BALANCER' | 'GATEWAY' | 'AUTHENTICATION' | 'IDENTITY' | 'DATABASE' | 'APPLICATION';
  status: 'OPERATIONAL' | 'DEGRADED' | 'DOWN';
  owner: string;          // e.g. "Network Team"
  riskScore: number;      // e.g. 85 (High)
  ip?: string;
  rack?: string;
  upstream: string[];     // IDs of upstream nodes
  downstream: string[];   // IDs of downstream nodes
  affectedServices: string[];
  openIncidents: string[];
  openProblems: string[];
  openChanges: string[];
}

export const MOCK_CMDB_GRAPH: CINode[] = [
  {
    id: 'ci-internet',
    name: 'Internet Gateway',
    kind: 'INTERNET',
    status: 'OPERATIONAL',
    owner: 'Network Team',
    riskScore: 20,
    upstream: [],
    downstream: ['ci-lb-01'],
    affectedServices: ['Corporate VPN', 'Corporate WiFi', 'M365 Cloud Access'],
    openIncidents: [],
    openProblems: [],
    openChanges: [],
  },
  {
    id: 'ci-lb-01',
    name: 'Load Balancer (F5 BIG-IP)',
    kind: 'LOAD_BALANCER',
    status: 'OPERATIONAL',
    owner: 'Network Team',
    riskScore: 45,
    ip: '10.0.1.1',
    rack: 'DC1-R04',
    upstream: ['ci-internet'],
    downstream: ['ci-vpngw-01'],
    affectedServices: ['Corporate VPN', 'CRM Portal'],
    openIncidents: [],
    openProblems: [],
    openChanges: [],
  },
  {
    id: 'ci-vpngw-01',
    name: 'VPN-GW-01 (Palo Alto PA-3220)',
    kind: 'GATEWAY',
    status: 'DEGRADED',
    owner: 'Network Team',
    riskScore: 88,
    ip: '10.0.4.1',
    rack: 'DC1-R12',
    upstream: ['ci-lb-01'],
    downstream: ['ci-auth-01'],
    affectedServices: ['Corporate VPN', 'Remote Access'],
    openIncidents: ['INC-10570', 'INC-10422'],
    openProblems: ['PRB-0081'],
    openChanges: ['CHG-0214'],
  },
  {
    id: 'ci-auth-01',
    name: 'NPS RADIUS Authentication',
    kind: 'AUTHENTICATION',
    status: 'DEGRADED',
    owner: 'Security Team',
    riskScore: 72,
    ip: '192.168.10.15',
    rack: 'DC1-R08',
    upstream: ['ci-vpngw-01'],
    downstream: ['ci-entra-id'],
    affectedServices: ['Corporate VPN', 'Corporate WiFi'],
    openIncidents: ['INC-10582'],
    openProblems: [],
    openChanges: [],
  },
  {
    id: 'ci-entra-id',
    name: 'Entra ID (Azure AD SSO)',
    kind: 'IDENTITY',
    status: 'OPERATIONAL',
    owner: 'Security Team',
    riskScore: 30,
    upstream: ['ci-auth-01'],
    downstream: [],
    affectedServices: ['Corporate VPN', 'Microsoft 365', 'CRM Portal', 'SAP Core'],
    openIncidents: [],
    openProblems: [],
    openChanges: [],
  },
];
