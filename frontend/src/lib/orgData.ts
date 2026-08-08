export interface DepartmentNode {
  name: string;
  manager: string;
}

export interface CompanyTenant {
  id: string;
  name: string;
  code: string;
  departments: DepartmentNode[];
  defaultSla: string;
  supportGroup: string;
}

export const MOCK_ORGANIZATIONS: CompanyTenant[] = [
  {
    id: 'comp-a',
    name: 'Company A (Tập đoàn Chính)',
    code: 'COMP-A',
    defaultSla: 'SLA Gold Standard',
    supportGroup: 'IT Tier 2 Support',
    departments: [
      { name: 'Finance & Accounting', manager: 'Nguyen Van A' },
      { name: 'Human Resources', manager: 'Trần Thị Bích' },
      { name: 'IT Infrastructure', manager: 'Phạm Thị Dung' },
    ],
  },
  {
    id: 'comp-b',
    name: 'Company B (Chi nhánh Miền Nam)',
    code: 'COMP-B',
    defaultSla: 'SLA Silver Standard',
    supportGroup: 'HCM Desk Support',
    departments: [
      { name: 'Sales & Marketing', manager: 'Lê Văn C' },
      { name: 'IT Support Team', manager: 'Lê Minh Công' },
    ],
  },
  {
    id: 'comp-c',
    name: 'Company C (Đơn vị Logistics)',
    code: 'COMP-C',
    defaultSla: 'SLA Bronze Standard',
    supportGroup: 'Logistics Desk',
    departments: [
      { name: 'Warehouse Operations', manager: 'Hoàng Văn Cường' },
    ],
  },
];
