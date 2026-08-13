type PortalPageSkeletonProps = {
  variant?: 'dashboard' | 'table';
};

/** Lightweight route-level fallback that mirrors portal content without a full-screen spinner. */
export default function PortalPageSkeleton({ variant = 'dashboard' }: PortalPageSkeletonProps) {
  return (
    <main className="route-loading" aria-busy="true" aria-label="Đang tải nội dung">
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ width: 'min(300px, 60%)', height: 26, marginBottom: 10 }} />
        <div className="skeleton" style={{ width: 'min(540px, 88%)', height: 14 }} />
      </div>
      {variant === 'dashboard' ? (
        <>
          <div className="dashboard-stat-grid" style={{ marginTop: 16 }}>
            {[0, 1, 2, 3].map((item) => <div className="card" style={{ height: 104 }} key={item} />)}
          </div>
          <div className="card" style={{ height: 250 }} />
        </>
      ) : (
        <div className="card" style={{ marginTop: 16, padding: 16 }}>
          <div className="skeleton" style={{ height: 36, marginBottom: 12 }} />
          {[0, 1, 2, 3, 4, 5].map((item) => <div className="skeleton" style={{ height: 46, marginTop: 8 }} key={item} />)}
        </div>
      )}
    </main>
  );
}
