import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Help Desk AI Agent | Enterprise ITSM',
  description: 'Hệ thống Help Desk AI thông minh — Phân loại tự động, RAG, HITL, SLA',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
