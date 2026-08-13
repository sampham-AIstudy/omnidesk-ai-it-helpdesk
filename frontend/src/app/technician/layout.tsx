import PortalShell from '@/components/PortalShell';

export default function TechnicianLayout({ children }: { children: React.ReactNode }) {
  return <PortalShell allowedRoles={['technician']}>{children}</PortalShell>;
}
