import PortalShell from '@/components/PortalShell';

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  return <PortalShell allowedRoles={['manager']}>{children}</PortalShell>;
}
