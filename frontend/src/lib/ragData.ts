export interface RAGMetrics {
  documentsCount: number;
  chunksCount: number;
  embeddingsCount: number;
  lastIndexingTime: string;
  retrieverEngine: string;
  rerankerEnabled: boolean;
  vectorDbStatus: 'HEALTHY' | 'DEGRADED';
}

export interface KBRetrievalResult {
  id: string; // e.g. "KB-0218"
  title: string;
  score: number;
  snippet: string;
  author: string;
}

export const MOCK_RAG_METRICS: RAGMetrics = {
  documentsCount: 12482,
  chunksCount: 84291,
  embeddingsCount: 84291,
  lastIndexingTime: '2 phút trước',
  retrieverEngine: 'Hybrid Search (Dense + Sparse BM25)',
  rerankerEnabled: true,
  vectorDbStatus: 'HEALTHY',
};

export const MOCK_RETRIEVAL_RESULTS: Record<string, KBRetrievalResult[]> = {
  default: [
    {
      id: 'KB-0218',
      title: 'VPN không thể kết nối sau khi đổi mật khẩu Active Directory',
      score: 0.94,
      snippet: 'Khi người dùng thực hiện đổi mật khẩu AD, profile Palo Alto GlobalProtect VPN cũ vẫn giữ lại NTLM hash cũ. Cần xóa credential cache tại %AppData%\\Palo Alto Networks\\GlobalProtect.',
      author: 'Lê Minh Công',
    },
    {
      id: 'KB-0129',
      title: 'Xóa Credential Cache và Reset SSL Certificate VPN Client',
      score: 0.87,
      snippet: 'Mở CMD với quyền Admin và chạy lệnh net stop PanGPS && net start PanGPS để xóa session cache.',
      author: 'Phạm Thị Dung',
    },
    {
      id: 'KB-0821',
      title: 'Hướng dẫn tự khắc phục lỗi Authentication Failed trên Windows 11',
      score: 0.74,
      snippet: 'Đảm bảo thời gian máy tính cá nhân đồng bộ đúng NTP server ntp.company.vn trước khi kết nối VPN.',
      author: 'System Bot',
    },
  ],
};
