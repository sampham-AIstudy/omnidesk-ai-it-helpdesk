export default function TechnicianLoading() {
  return (
    <main aria-busy="true" aria-label="Đang mở khu vực kỹ thuật viên" style={{ padding: '4px 0' }}>
      <div className="card" style={{ padding: 22, marginBottom: 16 }}>
        <div className="skeleton" style={{ width: 220, height: 24, marginBottom: 10 }} />
        <div className="skeleton" style={{ width: 360, maxWidth: '80%', height: 14 }} />
      </div>
      <div className="responsive-grid-2" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, marginBottom: 16 }}>
        {[1, 2, 3].map((item) => <div className="card" style={{ height: 82 }} key={item}><div className="skeleton" style={{ width: '55%', height: 12, marginBottom: 14 }} /><div className="skeleton" style={{ width: '25%', height: 25 }} /></div>)}
      </div>
      <div style={{ display: 'grid', gap: 10 }}>{[1, 2, 3, 4].map((item) => <div className="card" style={{ height: 115 }} key={item}><div className="skeleton" style={{ width: '45%', height: 14, marginBottom: 12 }} /><div className="skeleton" style={{ width: '75%', height: 12, marginBottom: 7 }} /><div className="skeleton" style={{ width: '58%', height: 12 }} /></div>)}</div>
    </main>
  );
}
