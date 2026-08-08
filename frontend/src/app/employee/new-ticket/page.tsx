'use client';

import { useMemo, useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'react-hot-toast';
import { 
  AlertCircle, AlertTriangle, BookOpen, Bot, CheckCircle2, Database, 
  FileUp, HelpCircle, Layers, Monitor, Send, ShieldAlert, UploadCloud, UserCheck, AlertOctagon, Info
} from 'lucide-react';
import AIProcessingModal from '@/components/AIProcessingModal';
import { PageHeader, Spinner } from '@/components/ui';
import { getErrorMessage } from '@/lib/utils';
import api from '@/lib/api';

const PRODUCTS = [
  { id: 'VPN_NETWORK', name: 'Kết Nối Mạng Nội Bộ & SSL VPN FortiClient', icon: '🌐' },
  { id: 'OFFICE_EMAIL', name: 'Hệ Thống Email & Bộ Ứng Dụng Văn Phòng (Outlook/Office 365)', icon: '📧' },
  { id: 'SAP_ERP', name: 'Phần Mềm Quản Trị Doanh Nghiệp (SAP ERP / Kế Toán / Nhan Su)', icon: '📊' },
  { id: 'HARDWARE_PC', name: 'Máy Tính Cá Nhân & Thiết Bị Phần Cứng (Workstation / Laptop)', icon: '💻' },
  { id: 'ACCESS_AUTH', name: 'Quản Lý Tài Khoản & Phân Quyền Truy Cập (Active Directory / IAM)', icon: '🔑' },
  { id: 'INFRA_SERVER', name: 'Hạ Tầng Máy Chủ & Cơ Sở Dữ Liệu (Server / Database / Storage)', icon: '🖥️' },
  { id: 'OTHER_PRODUCT', name: 'Khác (Ứng dụng / Dịch vụ chưa có trong danh sách trên)', icon: '⚙️' },
];

const CATEGORIES = [
  { id: 'REQUEST_TECH_SUPPORT', name: 'Sự Cố Kỹ Thuật (Incident Management)' },
  { id: 'REQUEST_ACCESS_PERMISSION', name: 'Yêu Cầu Dịch Vụ & Phân Quyền (Service Request)' },
  { id: 'SOFTWARE_SUPPORT', name: 'Hỗ Trợ Ứng Dụng Phần Mềm (Software Support)' },
  { id: 'HARDWARE_REQUEST', name: 'Yêu Cầu Trang Thiết Bị Phần Cứng (Hardware Provisioning)' },
  { id: 'OTHER_CATEGORY', name: 'Khác (Phân loại dịch vụ mới / Yêu cầu chưa có trong danh sách)' },
];

const URGENCY_LEVELS = [
  {
    id: 'LOW',
    label: 'Thấp',
    color: 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300',
    activeColor: 'border-slate-500 bg-slate-100 text-slate-900 ring-2 ring-slate-400',
    desc: 'Sự cố nhỏ, không ảnh hưởng trực tiếp đến tiến độ công việc hàng ngày.',
  },
  {
    id: 'MEDIUM',
    label: 'Trung Bình',
    color: 'border-blue-200 bg-blue-50/50 text-blue-800 hover:border-blue-300',
    activeColor: 'border-blue-600 bg-blue-100 text-blue-900 ring-2 ring-blue-500',
    desc: 'Bị gián đoạn công việc cá nhân nhưng vẫn có phương án tạm thời.',
  },
  {
    id: 'HIGH',
    label: 'Cao / Khẩn Cấp',
    color: 'border-rose-200 bg-rose-50/50 text-rose-800 hover:border-rose-300',
    activeColor: 'border-rose-600 bg-rose-100 text-rose-900 ring-2 ring-rose-500',
    desc: 'Ngưng trệ hoàn toàn công việc hoặc ảnh hưởng đến cả nhóm/hệ thống.',
  },
];

const SUB_ISSUES: Record<string, string[]> = {
  REQUEST_TECH_SUPPORT: [
    'Ứng dụng / Hệ thống bị treo, không phản hồi',
    'Lỗi văng ứng dụng / Tiến trình dịch vụ sập',
    'Lỗi xác thực domain / Hết hạn phiên làm việc',
    'Mất kết nối mạng nội bộ / Gián đoạn VPN',
    'Tốc độ xử lý hệ thống rất chậm / Quá tải tài nguyên',
    'Khác (Mô tả chi tiết sự cố & thông báo lỗi ở bên dưới)',
  ],
  REQUEST_ACCESS_PERMISSION: [
    'Yêu cầu đặt lại mật khẩu / Mở khóa tài khoản AD',
    'Cấp quyền truy cập thư mục dùng chung / Sharepoint',
    'Gia hạn / Khởi tạo Token SSL VPN',
    'Mở khóa tài khoản SAP bị giới hạn phiên',
    'Khác (Mô tả chi tiết sự cố & thông báo lỗi ở bên dưới)',
  ],
  SOFTWARE_SUPPORT: [
    'Email không gửi/nhận được từ đối tác ngoài',
    'Cần cài đặt / Nâng cấp phần mềm làm việc',
    'Lỗi kích hoạt / Hết hạn bản quyền phần mềm',
    'Khác (Mô tả chi tiết sự cố & thông báo lỗi ở bên dưới)',
  ],
  HARDWARE_REQUEST: [
    'Lỗi kết nối máy in / Máy quét văn phòng',
    'Lỗi màn hình / Cáp chuyển đổi tín hiệu',
    'Hỏng phím, chuột, thiết bị ngoại vi',
    'Đề xuất trang bị máy tính / Màn hình phụ mới',
    'Khác (Mô tả chi tiết sự cố & thông báo lỗi ở bên dưới)',
  ],
  OTHER_CATEGORY: [
    'Khác (Mô tả chi tiết sự cố & thông báo lỗi ở bên dưới)',
  ],
};

const getProductTag = (prodId: string) => {
  const map: Record<string, string> = {
    VPN_NETWORK: 'Mạng Nội Bộ & VPN',
    OFFICE_EMAIL: 'Email & Office',
    SAP_ERP: 'SAP ERP',
    HARDWARE_PC: 'Phần Cứng & Laptop',
    ACCESS_AUTH: 'Tài Khoản & Quyền',
    INFRA_SERVER: 'Máy Chủ & Hạ Tầng',
    OTHER_PRODUCT: 'Yêu Cầu Khác',
  };
  return map[prodId] || 'Yêu Cầu Khác';
};

const OS_OPTIONS = [
  'Windows 11 Enterprise',
  'Windows 10 Pro',
  'macOS Sonoma / Ventura',
  'iOS / Android Enterprise',
  'Ubuntu / Linux Workstation',
];

const LOCATION_OPTIONS = [
  'Làm việc từ xa (Remote / WFH VPN)',
  'Máy tính văn phòng trụ sở chính',
  'Hệ thống máy chủ / Datacenter',
  'Văn phòng chi nhánh / Nhà máy',
];

export default function NewTicketPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const prefillSubject = searchParams.get('subject') || '';
  const prefillCategory = searchParams.get('category') || '';

  const [product, setProduct] = useState(PRODUCTS[0].id);
  const [category, setCategory] = useState(prefillCategory && CATEGORIES.some(c => c.id === prefillCategory) ? prefillCategory : CATEGORIES[0].id);
  const [subIssue, setSubIssue] = useState(SUB_ISSUES[CATEGORIES[0].id][0]);
  const [urgency, setUrgency] = useState('MEDIUM');
  const [os, setOs] = useState(OS_OPTIONS[0]);
  const [location, setLocation] = useState(LOCATION_OPTIONS[0]);
  const [title, setTitle] = useState(prefillSubject);
  const [description, setDescription] = useState('');
  const [isProd, setIsProd] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const [createdTicket, setCreatedTicket] = useState<{ id: number; number: string } | null>(null);

  useEffect(() => {
    if (prefillSubject) setTitle(prefillSubject);
  }, [prefillSubject]);

  const selectedProduct = useMemo(() => PRODUCTS.find((p) => p.id === product), [product]);
  const selectedCategory = useMemo(() => CATEGORIES.find((c) => c.id === category), [category]);
  const selectedUrgency = useMemo(() => URGENCY_LEVELS.find((u) => u.id === urgency), [urgency]);

  const handleCategoryChange = (newCatId: string) => {
    setCategory(newCatId);
    const subList = SUB_ISSUES[newCatId] || [];
    if (subList.length > 0) setSubIssue(subList[0]);
  };

  const titleError = submitted && title.trim().length < 5 ? 'Vui lòng nhập tiêu đề ít nhất 5 ký tự.' : undefined;
  const descriptionError = submitted && description.trim().length < 10 ? 'Vui lòng mô tả ít nhất 10 ký tự.' : undefined;

  const handlePaste = (e: React.ClipboardEvent) => {
    if (e.clipboardData.files && e.clipboardData.files.length > 0) {
      const pastedFiles = Array.from(e.clipboardData.files);
      setFiles((prev) => [...prev, ...pastedFiles]);
      toast.success(`Đã dán ${pastedFiles.length} tệp/ảnh màn hình từ bộ nhớ tạm!`);
    }
  };

  const submitMutation = useMutation({
    mutationFn: async () => {
      // Read image files as base64 Data URLs so they can be viewed in detail page
      const fileDataUrls = await Promise.all(
        files.map(
          (file) =>
            new Promise<{ name: string; type: string; dataUrl: string }>((resolve) => {
              const reader = new FileReader();
              reader.onloadend = () =>
                resolve({ name: file.name, type: file.type, dataUrl: reader.result as string });
              reader.readAsDataURL(file);
            })
        )
      );

      const attachmentTags = fileDataUrls.map((item) =>
        item.type.startsWith('image/')
          ? `[Đính Kèm Ảnh: ${item.name}|${item.dataUrl}]`
          : `[Đính Kèm Tệp: ${item.name}]`
      );

      const fullDescription = [
        `[Hệ Thống / Dịch Vụ: ${selectedProduct?.name ?? product}]`,
        `[Phân Loại Dịch Vụ: ${selectedCategory?.name ?? category}]`,
        `[Mức Độ Khẩn Cấp: ${selectedUrgency?.label}]`,
        `[Mã Sự Cố: ${subIssue}]`,
        `[Môi Trường HĐH: ${os}]`,
        `[Vị Trí Vận Hành: ${location}]`,
        ...attachmentTags,
        '',
        '--- MÔ TẢ CHI TIẾT SỰ CỐ ---',
        description.trim(),
      ]
        .filter(Boolean)
        .join('\n');

      return (
        await api.post('/tickets', {
          title: `[${getProductTag(product)}] ${title.trim()}`,
          description: fullDescription,
          is_production_impact: isProd || urgency === 'HIGH',
        })
      ).data;
    },
    onSuccess: (data) => setCreatedTicket({ id: data.ticket_id, number: data.ticket_number }),
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleSubmit = () => {
    setSubmitted(true);
    if (title.trim().length < 5 || description.trim().length < 10) return;
    submitMutation.mutate();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const openTicket = () => {
    if (!createdTicket) return;
    toast.success(`Yêu cầu IT Help Desk ${createdTicket.number} đã được ghi nhận`);
    queryClient.invalidateQueries({ queryKey: ['my-tickets'] });
    router.push(`/employee/tickets/${createdTicket.id}`);
  };

  const backToList = () => {
    queryClient.invalidateQueries({ queryKey: ['my-tickets'] });
    router.push('/employee/tickets');
  };

  return (
    <div onPaste={handlePaste} className="space-y-6">
      <PageHeader
        title="Gửi Yêu Cầu Hỗ Trợ Kỹ Thuật (Create Ticket Form)"
        subtitle="Vui lòng điền đầy đủ các thông tin bên dưới để AI Agent tra cứu KB hoặc chuyển tiếp cho Chuyên viên IT."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* MAIN FORM CONTAINER */}
        <div className="lg:col-span-8 space-y-6">

          {/* BLOCK 1: PRODUCT & CATEGORY */}
          <div className="glass-card-light rounded-3xl p-6 space-y-5">
            <div className="flex items-center gap-2.5 pb-4 border-b border-slate-200">
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                1
              </div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Hệ Thống & Mức Độ Khẩn Cấp (Urgency)
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Hệ Thống / Dịch Vụ Ảnh Hưởng *
                </label>
                <select
                  className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={product}
                  onChange={(e) => setProduct(e.target.value)}
                >
                  {PRODUCTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.icon} {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Phân Loại Sự Cố *
                </label>
                <select
                  className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={category}
                  onChange={(e) => handleCategoryChange(e.target.value)}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* URGENCY SELECTOR WITH TOOLTIPS */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Mức Độ Khẩn Cấp (Urgency Level) *
                </label>
                <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1">
                  <Info size={13} />
                  Chọn mức phù hợp để tránh lạm dụng ưu tiên
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                {URGENCY_LEVELS.map((u) => (
                  <button
                    type="button"
                    key={u.id}
                    onClick={() => setUrgency(u.id)}
                    className={`p-3.5 rounded-2xl border text-left transition-all ${
                      urgency === u.id ? u.activeColor : u.color
                    }`}
                  >
                    <div className="font-bold text-xs">{u.label}</div>
                    <div className="text-[11px] opacity-80 mt-1 line-clamp-2 leading-snug">{u.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* BLOCK 2: SUB-ISSUE & LOCATION */}
          <div className="glass-card-light rounded-3xl p-6 space-y-5">
            <div className="flex items-center gap-2.5 pb-4 border-b border-slate-200">
              <div className="w-8 h-8 rounded-xl bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold">
                2
              </div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Chi Tiết Sự Cố & Môi Trường Vận Hành
              </h2>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Mã Sự Cố Cụ Thể *
              </label>
              <select
                className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                value={subIssue}
                onChange={(e) => setSubIssue(e.target.value)}
              >
                {(SUB_ISSUES[category] || []).map((sub) => (
                  <option key={sub} value={sub}>
                    {sub}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Vị Trí Vận Hành *
                </label>
                <select
                  className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-sm font-medium text-slate-900"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                >
                  {LOCATION_OPTIONS.map((loc) => (
                    <option key={loc} value={loc}>{loc}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Hệ Điều Hành *
                </label>
                <select
                  className="w-full px-4 py-2.5 bg-white rounded-xl border border-slate-300 text-sm font-medium text-slate-900"
                  value={os}
                  onChange={(e) => setOs(e.target.value)}
                >
                  {OS_OPTIONS.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* BLOCK 3: TITLE, DESCRIPTION & DROPZONE */}
          <div className="glass-card-light rounded-3xl p-6 space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Tiêu Đề Yêu Cầu *
              </label>
              <input
                className="w-full px-4 py-3 bg-white rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ví dụ: Không thể kết nối SSL VPN FortiClient từ môi trường Remote WFH"
              />
              {titleError && <div className="text-xs font-bold text-rose-600 mt-1">{titleError}</div>}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Mô Tả Chi Tiết Sự Cố & Thông Báo Lỗi *
              </label>
              <textarea
                className="w-full px-4 py-3 bg-white rounded-xl border border-slate-300 text-sm font-medium text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Mô tả chi tiết triệu chứng, mã lỗi (Error Code), các bước bạn đã làm... Bạn cũng có thể nhấn Ctrl+V để dán ảnh màn hình trực tiếp vào đây."
                rows={6}
              />
              {descriptionError && <div className="text-xs font-bold text-rose-600 mt-1">{descriptionError}</div>}
            </div>

            {/* DROPZONE AREA */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Tệp Đính Kèm / Kéo Thả & Dán Ảnh (Ctrl+V)
              </label>
              <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-300 rounded-2xl bg-slate-50/80 hover:bg-blue-50/50 hover:border-blue-400 transition-all cursor-pointer text-center">
                <UploadCloud size={32} className="text-slate-400 mb-2" />
                <span className="text-sm font-semibold text-blue-600">Kéo và thả file hoặc nhấn Ctrl + V để dán ảnh màn hình</span>
                <span className="text-xs text-slate-400 mt-1">Định dạng hỗ trợ: PNG, JPG, PDF, TXT, LOG (Tối đa 10MB)</span>
                <input type="file" multiple onChange={handleFileUpload} className="hidden" />
              </label>
              {files.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {files.map((f, i) => (
                    <span key={i} className="px-3 py-1 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-xs font-semibold">
                      📎 {f.name} ({(f.size / 1024).toFixed(0)}KB)
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* PRODUCTION IMPACT SWITCH */}
            <label className={`flex items-center gap-3 p-4 rounded-2xl border cursor-pointer transition-all ${
              isProd ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'
            }`}>
              <input
                type="checkbox"
                checked={isProd}
                onChange={(e) => setIsProd(e.target.checked)}
                className="w-5 h-5 text-rose-600 rounded focus:ring-rose-500"
              />
              <div>
                <div className="text-xs font-bold text-slate-900">Ảnh Hưởng Hệ Thống Production / Vận Hành Cốt Lõi</div>
                <div className="text-[11px] text-slate-500 font-medium">Đánh dấu khi sự cố làm ngưng trệ máy chủ chính hoặc toàn bộ phòng ban.</div>
              </div>
            </label>

            {/* SUBMIT BUTTON */}
            <button
              onClick={handleSubmit}
              disabled={submitMutation.isPending}
              className="w-full py-4 shimmer-button text-white font-bold text-sm rounded-2xl flex items-center justify-center gap-2 active:scale-98 transition-transform"
            >
              {submitMutation.isPending ? <Spinner size={18} /> : <Send size={18} />}
              <span>Gửi Yêu Cầu & Kích Hoạt Tra Cứu AI Help Desk</span>
            </button>
          </div>
        </div>

        {/* SIDEBAR GUIDANCE */}
        <div className="lg:col-span-4 space-y-4 sticky top-24">
          <div className="glass-card-light rounded-3xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-blue-600 font-bold text-sm">
              <Bot size={20} />
              <span>Quy Trình Xử Lý AI Engine</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Sau khi bạn bấm gửi ticket, AI Agent sẽ tức thì phân tích triệu chứng, tra cứu 392+ tài liệu KB chuẩn Microsoft và gửi lại quy trình xử lý từng bước.
            </p>
            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs font-semibold text-emerald-800 space-y-1">
              <div>✅ Tự động khôi phục tài khoản SSPR</div>
              <div>✅ Hướng dẫn cấu hình VPN / Wi-Fi</div>
              <div>✅ Sửa lỗi Outlook PST & BSOD</div>
            </div>
          </div>
        </div>

      </div>

      {createdTicket && (
        <AIProcessingModal
          ticketId={createdTicket.id}
          ticketNumber={createdTicket.number}
          onViewTicket={openTicket}
          onBackToList={backToList}
        />
      )}
    </div>
  );
}

