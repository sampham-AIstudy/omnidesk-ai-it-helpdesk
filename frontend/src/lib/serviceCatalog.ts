export type ServiceCatalogItem = {
  service_name: string;
  category: string;
  fulfillment_group: string;
  approval_roles: string[];
  risk_level: 'low' | 'medium' | 'high';
  sla_hours: number;
};

export const SERVICE_CATEGORY_META: Record<string, { label: string; description: string }> = {
  hardware: { label: 'Hardware', description: 'Thiết bị, phụ kiện và môi trường làm việc do Workplace IT quản lý.' },
  access: { label: 'Access', description: 'Quyền truy cập vào hệ thống nội bộ và tài nguyên doanh nghiệp.' },
  software: { label: 'Software', description: 'License, phần mềm nghiệp vụ và bảo vệ endpoint.' },
  accounts: { label: 'Accounts', description: 'Tài khoản công ty, email và hỗ trợ định danh.' },
  network: { label: 'Network', description: 'Kết nối mạng, địa chỉ IP và thay đổi có kiểm soát.' },
  onboarding: { label: 'Workplace support', description: 'Thiết bị và hỗ trợ tại nơi làm việc.' },
};

export function formatServiceSla(hours: number): string {
  return `${hours} giờ làm việc`;
}

export function formatApproval(roles: string[]): string {
  if (!roles.length) return 'Không yêu cầu';
  return roles.map((role) => role.replaceAll('_', ' ')).join(', ');
}
