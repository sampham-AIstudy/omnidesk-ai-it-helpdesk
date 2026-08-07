'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export default function ErrorPage({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="route-error" role="alert">
      <div className="card">
        <AlertTriangle size={30} aria-hidden="true" />
        <h1>Trang chưa thể hiển thị</h1>
        <p>Đã xảy ra lỗi ngoài dự kiến. Bạn có thể thử tải lại phần nội dung này.</p>
        <button className="btn-primary" onClick={unstable_retry}>
          <RotateCcw size={16} aria-hidden="true" /> Thử lại
        </button>
      </div>
    </main>
  );
}
