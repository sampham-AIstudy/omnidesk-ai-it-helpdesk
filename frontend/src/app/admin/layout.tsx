import PortalShell from '@/components/PortalShell';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <PortalShell allowedRoles={['admin']}>{children}</PortalShell>;
}
