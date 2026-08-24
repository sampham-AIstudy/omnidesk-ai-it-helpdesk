import {
  Network,
  Cloud,
  ShieldCheck,
  Phone,
  MessageSquare,
  BellRing,
} from 'lucide-react';

export type ContactMethod = 'CALL' | 'SMS' | 'APP';

export interface OnCallMember {
  name: string;
  phone: string;
  via: ContactMethod;
  until: string;
  shiftStart: string;
  shiftEnd: string;
}

export interface EscalationStep {
  level: number;
  target: string;
  targetPerson: string;
  delay: string;
  delayMin: number;
  on: 'NO_ACK' | 'ACK_NO_FIX' | 'AUTO';
  to: 'PRIMARY' | 'SECONDARY' | 'MANAGER' | 'TEAM';
}

export interface OnCallTeam {
  id: string;               // e.g. "network"
  name: string;             // e.g. "Network"
  iconName: 'Network' | 'Cloud' | 'ShieldCheck';
  primary: OnCallMember;
  secondary?: OnCallMember;
  rotation: string;         // e.g. "1 tuần / rotation"
  members: string[];
  escalation: EscalationStep[];
  color: 'cyan' | 'amber' | 'red' | 'emerald';
  nextShiftInfo: string;
}

export interface OnCallOverride {
  id: string;
  teamId: string;
  teamName: string;
  originalPerson: string;
  overridePerson: string;
  shiftTime: string;
  reason: string;
  status: 'ACTIVE' | 'EXPIRED';
}

export const ON_CALL_TEAMS: OnCallTeam[] = [
  {
    id: 'network',
    name: 'Network',
    iconName: 'Network',
    color: 'cyan',
    rotation: '1 tuần · 5 thành viên',
    nextShiftInfo: 'Nguyen C (08/08 → 14/08)',
    primary: {
      name: 'Nguyen Van A',
      phone: '0932 123 456',
      via: 'CALL',
      until: '08:00',
      shiftStart: '20:00',
      shiftEnd: '08:00',
    },
    secondary: {
      name: 'Tran Van B',
      phone: '0912 987 654',
      via: 'SMS',
      until: '08:00',
      shiftStart: '20:00',
      shiftEnd: '08:00',
    },
    members: ['Nguyen Van A', 'Tran Van B', 'Nguyen Van C', 'Hoang Van D', 'Lê Minh Công'],
    escalation: [
      {
        level: 1,
        target: 'Network Primary',
        targetPerson: 'Nguyen Van A',
        delay: '0 MIN',
        delayMin: 0,
        on: 'NO_ACK',
        to: 'PRIMARY',
      },
      {
        level: 2,
        target: 'Network Secondary',
        targetPerson: 'Tran Van B',
        delay: '5 MIN',
        delayMin: 5,
        on: 'NO_ACK',
        to: 'SECONDARY',
      },
      {
        level: 3,
        target: 'IT Manager',
        targetPerson: 'Phạm Thị Dung',
        delay: '10 MIN',
        delayMin: 10,
        on: 'NO_ACK',
        to: 'MANAGER',
      },
    ],
  },
  {
    id: 'cloud',
    name: 'Cloud & Infrastructure',
    iconName: 'Cloud',
    color: 'amber',
    rotation: '2 tuần · 3 thành viên',
    nextShiftInfo: 'Dang E (15/08 → 29/08)',
    primary: {
      name: 'Le Van C',
      phone: '0909 555 111',
      via: 'APP',
      until: '20:00',
      shiftStart: '08:00',
      shiftEnd: '20:00',
    },
    members: ['Le Van C', 'Dang E', 'Vu F'],
    escalation: [
      {
        level: 1,
        target: 'Cloud Primary',
        targetPerson: 'Le Van C',
        delay: '0 MIN',
        delayMin: 0,
        on: 'NO_ACK',
        to: 'PRIMARY',
      },
      {
        level: 2,
        target: 'Cloud Lead',
        targetPerson: 'Dang E',
        delay: '10 MIN',
        delayMin: 10,
        on: 'NO_ACK',
        to: 'SECONDARY',
      },
      {
        level: 3,
        target: 'IT Director',
        targetPerson: 'Phạm Thị Dung',
        delay: '20 MIN',
        delayMin: 20,
        on: 'NO_ACK',
        to: 'MANAGER',
      },
    ],
  },
  {
    id: 'security',
    name: 'SOC & Cyber Security',
    iconName: 'ShieldCheck',
    color: 'red',
    rotation: '1 tuần · 4 thành viên',
    nextShiftInfo: 'Ngo H (08/08 → 14/08)',
    primary: {
      name: 'Pham Van D',
      phone: '0988 222 333',
      via: 'CALL',
      until: '08:00',
      shiftStart: '20:00',
      shiftEnd: '08:00',
    },
    secondary: {
      name: 'Le Van E',
      phone: '0966 777 888',
      via: 'SMS',
      until: '08:00',
      shiftStart: '20:00',
      shiftEnd: '08:00',
    },
    members: ['Pham Van D', 'Le Van E', 'Ngo H', 'Bui K'],
    escalation: [
      {
        level: 1,
        target: 'SOC Duty Analyst',
        targetPerson: 'Pham Van D',
        delay: '0 MIN',
        delayMin: 0,
        on: 'NO_ACK',
        to: 'PRIMARY',
      },
      {
        level: 2,
        target: 'SOC Lead Analyst',
        targetPerson: 'Le Van E',
        delay: '5 MIN',
        delayMin: 5,
        on: 'NO_ACK',
        to: 'SECONDARY',
      },
      {
        level: 3,
        target: 'CISO / Head of Security',
        targetPerson: 'Trịnh Văn G',
        delay: '15 MIN',
        delayMin: 15,
        on: 'NO_ACK',
        to: 'MANAGER',
      },
    ],
  },
];

export const MOCK_OVERRIDES: OnCallOverride[] = [
  {
    id: 'ovr-1',
    teamId: 'security',
    teamName: 'Security',
    originalPerson: 'Pham Van D',
    overridePerson: 'Le Van E',
    shiftTime: '06/08 20:00 → 07/08 08:00',
    reason: 'Gia đình có việc đột xuất',
    status: 'ACTIVE',
  },
  {
    id: 'ovr-2',
    teamId: 'network',
    teamName: 'Network',
    originalPerson: 'Tran Van B',
    overridePerson: 'Nguyen Van C',
    shiftTime: '01/08 08:00 → 01/08 20:00',
    reason: 'Đi công tác chi nhánh Đà Nẵng',
    status: 'EXPIRED',
  },
];
