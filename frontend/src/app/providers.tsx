'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useState } from 'react';
import CommandPalette from '@/components/CommandPalette';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <CommandPalette />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#0d1526',
            border: '1px solid rgba(255,255,255,0.08)',
            color: '#f1f5f9',
            fontFamily: 'Inter, sans-serif',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#0d1526' } },
          error:   { iconTheme: { primary: '#f43f5e', secondary: '#0d1526' } },
        }}
      />
    </QueryClientProvider>
  );
}
