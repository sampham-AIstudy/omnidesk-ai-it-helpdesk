'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Laptop, Plus, ShieldCheck, Download, Search, Server, KeyRound, HardDrive } from 'lucide-react';
import { PageHeader } from '@/components/ui';

interface CMDBAsset {
  id: string;
  name: string;
  category: string;
  serial: string;
  assignedUser: string;
  department: string;
  status: 'In Use' | 'In Stock' | 'Maintenance';
  warrantyUntil: string;
  licenseMaster: string;
}

export default function AdminCMDBPage() {
  const [assets, setAssets] = useState<CMDBAsset[]>([
    {
      id: '1',
      name: 'Dell Latitude 5420 Laptop Workstation',
      category: 'Workstation',
      serial: 'DL-99482-VN',
      assignedUser: 'Nguyễn Văn An',
      department: 'Phòng Kế Toán',
      status: 'In Use',
      warrantyUntil: '15/12/2027',
      licenseMaster: 'Office 365 E3 Enterprise',
    },
    {
      id: '2',
      name: 'MacBook Pro M2 Max 16-inch',
      category: 'Workstation',
      serial: 'MB-88231-US',
      assignedUser: 'Trần Thị Bích (VIP)',
      department: 'Ban Giám Đốc',
      status: 'In Use',
      warrantyUntil: '10/08/2028',
      licenseMaster: 'Adobe Creative Cloud + M365',
    },
    {
      id: '3',
      name: 'Dell PowerEdge R750 Rack Server',
      category: 'Server Hardware',
      serial: 'PE-R750-001',
      assignedUser: 'Hạ Tầng Datacenter',
      department: 'Phòng IT System',
      status: 'In Use',
      warrantyUntil: '20/01/2029',
      licenseMaster: 'Windows Server 2022 Datacenter',
    },
  ]);

  const [search, setSearch] = useState('');

  const filteredAssets = assets.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.serial.toLowerCase().includes(search.toLowerCase()) ||
      a.assignedUser.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản Lý Kho Cấu Hình Tài Sản Hạ Tầng (CMDB Master Inventory)"
        subtitle="Dành riêng cho System Administrator: Quản lý toàn bộ máy tính, máy chủ, thiết bị mạng, số serial number & bản quyền phần mềm gốc."
      />

      <div className="glass-card-light rounded-3xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative flex-1 w-full">
            <Search size={16} className="absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Tra cứu theo tên thiết bị, mã Serial Number hoặc người sử dụng..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white rounded-xl border border-slate-300 text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => toast.success('Đã nhập dữ liệu CMDB từ Active Directory!')}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all"
            >
              Đồng bộ AD CMDB
            </button>
            <button
              onClick={() => toast.success('Đã mở form nhập kho thiết bị mới!')}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-md shadow-blue-500/20 transition-all flex items-center gap-1.5"
            >
              <Plus size={15} />
              <span>Thêm Thiết Bị Mới</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">Tên Thiết Bị / Máy Chủ</th>
                <th className="py-3.5 px-4">Phân Loại</th>
                <th className="py-3.5 px-4">Mã Serial Number</th>
                <th className="py-3.5 px-4">Người Sử Dụng</th>
                <th className="py-3.5 px-4">Phòng Ban</th>
                <th className="py-3.5 px-4">Trạng Thái Kho</th>
                <th className="py-3.5 px-4">Hạn Bảo Hành</th>
                <th className="py-3.5 px-4">Bản Quyền Phần Mềm</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {filteredAssets.map((asset) => (
                <tr key={asset.id} className="hover:bg-blue-50/30 transition-colors">
                  <td className="py-4 px-4 font-bold text-slate-900">{asset.name}</td>
                  <td className="py-4 px-4 text-slate-600">{asset.category}</td>
                  <td className="py-4 px-4 font-mono font-bold text-blue-600">{asset.serial}</td>
                  <td className="py-4 px-4 font-semibold text-slate-800">{asset.assignedUser}</td>
                  <td className="py-4 px-4 text-slate-500">{asset.department}</td>
                  <td className="py-4 px-4">
                    <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                      {asset.status}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-emerald-600 font-semibold">{asset.warrantyUntil}</td>
                  <td className="py-4 px-4 text-slate-700">{asset.licenseMaster}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
