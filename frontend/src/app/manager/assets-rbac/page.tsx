'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { ShieldCheck, Laptop, Check, X, KeyRound, Server } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface Asset {
  id: string;
  name: string;
  serial: string;
  assignedTo: string;
  department: string;
  warrantyExpire: string;
  licenseStatus: string;
}

export default function RBACAssetsPage() {
  const [activeTab, setActiveTab] = useState<'cmdb' | 'rbac'>('cmdb');

  const [assets] = useState<Asset[]>([
    {
      id: '1',
      name: 'Dell Latitude 5420 Laptop Workstation',
      serial: 'DL-99482-VN',
      assignedTo: 'Nguyễn Văn An',
      department: 'Phòng Kế Toán',
      warrantyExpire: '15/12/2027',
      licenseStatus: 'Office 365 E3 Active',
    },
    {
      id: '2',
      name: 'MacBook Pro M2 Max 16-inch',
      serial: 'MB-88231-US',
      assignedTo: 'Trần Thị Bình',
      department: 'Ban Giám Đốc (VIP)',
      warrantyExpire: '10/08/2028',
      licenseStatus: 'Adobe Creative Cloud + M365',
    },
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Phân Quyền & Kho Tài Sản CNTT (RBAC & CMDB)"
        subtitle="Quản lý ma trận phân quyền người dùng (Role Matrix) và kho thiết bị phần cứng, mã serial, hạn bảo hành & bản quyền phần mềm."
      />

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('cmdb')}
          className={`px-5 py-2.5 rounded-2xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'cmdb' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Laptop size={15} />
          <span>Kho Tài Sản CNTT (CMDB Asset Inventory)</span>
        </button>
        <button
          onClick={() => setActiveTab('rbac')}
          className={`px-5 py-2.5 rounded-2xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'rbac' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <ShieldCheck size={15} />
          <span>Ma Trận Phân Quyền Vai Trò (RBAC Matrix)</span>
        </button>
      </div>

      {activeTab === 'cmdb' ? (
        /* CMDB Inventory Table */
        <div className="glass-card-light rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Danh Sách Thiết Bị & Bản Quyền Phần Mềm Doanh Nghiệp
            </h3>
            <button onClick={() => toast.success('Đã xuất danh sách CMDB ra file Excel!')} className="px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-xl text-xs font-bold">
              Xuất Excel (.xlsx)
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-4">Tên Thiết Bị / Máy Chủ</th>
                  <th className="py-3.5 px-4">Số Serial Number</th>
                  <th className="py-3.5 px-4">Người Sở Hữu</th>
                  <th className="py-3.5 px-4">Phòng Ban</th>
                  <th className="py-3.5 px-4">Hạn Bảo Hành</th>
                  <th className="py-3.5 px-4">Bản Quyền Phần Mềm</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {assets.map((a) => (
                  <tr key={a.id} className="hover:bg-blue-50/30 transition-colors">
                    <td className="py-4 px-4 font-bold text-slate-900">{a.name}</td>
                    <td className="py-4 px-4 font-mono font-bold text-blue-600">{a.serial}</td>
                    <td className="py-4 px-4 text-slate-700">{a.assignedTo}</td>
                    <td className="py-4 px-4 text-slate-600">{a.department}</td>
                    <td className="py-4 px-4 text-emerald-600 font-semibold">{a.warrantyExpire}</td>
                    <td className="py-4 px-4">
                      <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                        {a.licenseStatus}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* RBAC Matrix Table */
        <div className="glass-card-light rounded-3xl p-6 space-y-4">
          <h3 className="font-bold text-slate-900 text-base" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Ma Trận Phân Quyền Vai Trò Người Dùng (Role-Based Access Control)
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-4">Tính Năng / Quyền Hạn</th>
                  <th className="py-3.5 px-4 text-center">Employee</th>
                  <th className="py-3.5 px-4 text-center">Tech Level 1</th>
                  <th className="py-3.5 px-4 text-center">Tech Level 2</th>
                  <th className="py-3.5 px-4 text-center">Admin / Manager</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {[
                  { name: 'Tạo Ticket & Chat với AI Agent', emp: true, t1: true, t2: true, adm: true },
                  { name: 'Tiếp nhận & Đóng Ticket hàng đợi', emp: false, t1: true, t2: true, adm: true },
                  { name: 'Duyệt HITL & Phản hồi riêng nội bộ', emp: false, t1: true, t2: true, adm: true },
                  { name: 'Cấu hình Tự động hóa & SLA Matrix', emp: false, t1: false, t2: false, adm: true },
                  { name: 'Xem Báo cáo Wallboard & Analytics', emp: false, t1: false, t2: true, adm: true },
                ].map((row, idx) => (
                  <tr key={idx} className="hover:bg-blue-50/30 transition-colors">
                    <td className="py-4 px-4 font-bold text-slate-900">{row.name}</td>
                    <td className="py-4 px-4 text-center">{row.emp ? <Check className="mx-auto text-emerald-600" size={18} /> : <X className="mx-auto text-slate-300" size={18} />}</td>
                    <td className="py-4 px-4 text-center">{row.t1 ? <Check className="mx-auto text-emerald-600" size={18} /> : <X className="mx-auto text-slate-300" size={18} />}</td>
                    <td className="py-4 px-4 text-center">{row.t2 ? <Check className="mx-auto text-emerald-600" size={18} /> : <X className="mx-auto text-slate-300" size={18} />}</td>
                    <td className="py-4 px-4 text-center">{row.adm ? <Check className="mx-auto text-emerald-600" size={18} /> : <X className="mx-auto text-slate-300" size={18} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
