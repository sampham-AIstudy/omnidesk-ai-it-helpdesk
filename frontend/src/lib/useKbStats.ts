'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export function useKbStats() {
  const { data } = useQuery({
    queryKey: ['public-kb-stats'],
    queryFn: async () => {
      try {
        const res = await api.get<{ total_kb_count: number }>('/kb-stats');
        return res.data;
      } catch {
        return { total_kb_count: 227 };
      }
    },
    staleTime: 60000,
  });

  const count = data?.total_kb_count && data.total_kb_count > 0 ? data.total_kb_count : 227;

  return {
    kbCount: count,
    kbText: `${count}+`,
    kbDocs: `${count}+ KB Docs`,
  };
}
