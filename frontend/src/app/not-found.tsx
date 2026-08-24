import Link from 'next/link';
import { FileQuestion } from 'lucide-react';

export default function NotFound() {
  return (
    <main className="route-error">
      <div className="card">
        <FileQuestion size={30} aria-hidden="true" />
        <h1>Không tìm thấy nội dung</h1>
        <p>Trang hoặc ticket bạn đang tìm không tồn tại, đã bị xóa hoặc bạn không có quyền truy cập.</p>
        <Link className="btn-primary" href="/">Về trang chính</Link>
      </div>
    </main>
  );
}
