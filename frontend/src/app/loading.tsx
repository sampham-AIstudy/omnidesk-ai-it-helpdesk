import { Skeleton } from '@/components/ui';

export default function Loading() {
  return (
    <main className="route-loading" aria-label="Đang tải trang" aria-busy="true">
      <Skeleton height={32} width="42%" />
      <Skeleton height={16} width="64%" />
      <div className="dashboard-stat-grid" style={{ marginTop: 24 }}>
        {[0, 1, 2, 3].map((item) => <Skeleton key={item} height={108} />)}
      </div>
      <Skeleton height={240} />
    </main>
  );
}
