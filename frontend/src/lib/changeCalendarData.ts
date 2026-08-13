export interface ChangeCalendarItem {
  id: string; // e.g. "CHG-102"
  title: string;
  type: 'STANDARD' | 'NORMAL' | 'EMERGENCY';
  risk: 'HIGH' | 'MEDIUM' | 'LOW';
  targetCi: string;
  scheduledDate: string; // e.g. "12/08/2026"
  owner: string;
  hasCollision?: boolean;
  collisionDetails?: string;
}

export const MOCK_CHANGE_CALENDAR: ChangeCalendarItem[] = [
  {
    id: 'CHG-102',
    title: 'Database Cluster Firmware Upgrade',
    type: 'NORMAL',
    risk: 'HIGH',
    targetCi: 'DB-PROD-01',
    scheduledDate: '12/08/2026',
    owner: 'DBA Team',
    hasCollision: true,
    collisionDetails: 'Collision detected! CHG-102 modifies DB-PROD-01 while CHG-109 depends on DB-PROD-01.',
  },
  {
    id: 'CHG-109',
    title: 'Palo Alto Firewall Rule Refresh',
    type: 'STANDARD',
    risk: 'MEDIUM',
    targetCi: 'FW-EDGE-01',
    scheduledDate: '12/08/2026',
    owner: 'Network Team',
    hasCollision: true,
    collisionDetails: 'CHG-109 depends on DB-PROD-01 which is modified by CHG-102 at the same window.',
  },
  {
    id: 'CHG-115',
    title: 'Emergency Patch Exchange Server',
    type: 'EMERGENCY',
    risk: 'HIGH',
    targetCi: 'EXCH-01',
    scheduledDate: '14/08/2026',
    owner: 'Cloud Team',
  },
];
