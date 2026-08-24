'use client';

import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ChevronRight, Clock3, ShieldCheck, UsersRound } from 'lucide-react';

import api from '@/lib/api';
import { formatApproval, formatServiceSla, SERVICE_CATEGORY_META, type ServiceCatalogItem } from '@/lib/serviceCatalog';

function CategoryContent() {
  const params = useParams<{ category: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const categoryMeta = SERVICE_CATEGORY_META[params.category];
  const catalogQuery = useQuery({
    queryKey: ['service-catalog'],
    queryFn: async () => (await api.get<{ items: ServiceCatalogItem[] }>('/service-requests/catalog')).data.items,
    staleTime: 60_000,
  });

  if (!categoryMeta) {
    return <main className="mx-auto max-w-4xl py-10"><p className="text-sm text-slate-600">Không tìm thấy danh mục dịch vụ.</p><Link href="/employee/catalog" className="mt-4 inline-block text-sm font-semibold text-blue-700">Quay lại catalog</Link></main>;
  }

  if (catalogQuery.isLoading) {
    return <main className="mx-auto max-w-5xl py-10"><div className="skeleton h-7 w-40" /><div className="mt-6 skeleton h-72 w-full" /></main>;
  }

  if (catalogQuery.isError) {
    return <main className="mx-auto max-w-5xl py-10"><div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">Không thể tải chi tiết dịch vụ từ hệ thống. Vui lòng thử lại sau.</div></main>;
  }

  const services = (catalogQuery.data ?? []).filter((item) => item.category === params.category);
  const service = services.find((item) => item.service_name === searchParams.get('service'));

  if (!service) {
    return <main className="mx-auto max-w-5xl pb-10">
      <nav className="mb-6 flex items-center gap-2 text-xs text-slate-500"><Link href="/employee/catalog" className="hover:text-blue-700">Service catalog</Link><ChevronRight size={14} /><span>{categoryMeta.label}</span></nav>
      <header className="mb-7"><h1 className="text-3xl font-semibold tracking-tight text-slate-950">{categoryMeta.label}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{categoryMeta.description}</p></header>
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {services.map((item) => <article key={item.service_name} className="flex flex-col gap-4 border-b border-slate-200 p-5 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="font-semibold text-slate-950">{item.service_name}</h2><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600"><span>{item.fulfillment_group}</span><span>Approval: {formatApproval(item.approval_roles)}</span><span>SLA: {formatServiceSla(item.sla_hours)}</span></div></div>
          <button type="button" onClick={() => router.push(`/employee/catalog/${params.category}?service=${encodeURIComponent(item.service_name)}`)} className="btn-primary shrink-0">Xem chi tiết <ChevronRight size={15} /></button>
        </article>)}
      </section>
    </main>;
  }

  return <main className="mx-auto max-w-5xl pb-10">
    <nav className="mb-6 flex items-center gap-2 text-xs text-slate-500"><Link href="/employee/catalog" className="hover:text-blue-700">Service catalog</Link><ChevronRight size={14} /><Link href={`/employee/catalog/${params.category}`} className="hover:text-blue-700">{categoryMeta.label}</Link><ChevronRight size={14} /><span className="text-slate-700">{service.service_name}</span></nav>
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <header className="border-b border-slate-200 bg-slate-50 px-6 py-7 md:px-8"><p className="text-xs font-semibold text-blue-700">{categoryMeta.label}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{service.service_name}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Thông tin định tuyến, phê duyệt và SLA bên dưới được lấy từ Service Catalog của hệ thống.</p></header>
      <div className="grid gap-8 p-6 md:grid-cols-[minmax(0,1fr)_280px] md:p-8"><div><h2 className="text-base font-semibold text-slate-900">Trước khi gửi yêu cầu</h2><p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">Chuẩn bị thông tin cần thiết cho dịch vụ. Form tiếp theo sẽ kiểm tra các trường bắt buộc trước khi gửi vào workflow.</p><div className="mt-8 flex flex-wrap gap-3"><button type="button" onClick={() => router.push(`/employee/requests/new?category=${service.category}&item=${encodeURIComponent(service.service_name)}`)} className="btn-primary h-10 px-5">Tạo yêu cầu <ChevronRight size={16} /></button><Link href={`/employee/catalog/${params.category}`} className="btn-ghost h-10"><ArrowLeft size={15} />Quay lại</Link></div></div>
        <aside className="rounded-xl border border-slate-200 bg-slate-50 p-5"><div className="flex gap-3"><UsersRound size={17} className="shrink-0 text-blue-700" /><div><p className="text-xs font-semibold text-slate-800">Nhóm xử lý</p><p className="mt-1 text-sm text-slate-600">{service.fulfillment_group}</p></div></div><div className="mt-5 flex gap-3 border-t border-slate-200 pt-5"><ShieldCheck size={17} className="shrink-0 text-blue-700" /><div><p className="text-xs font-semibold text-slate-800">Phê duyệt</p><p className="mt-1 text-sm text-slate-600">{formatApproval(service.approval_roles)}</p></div></div><div className="mt-5 flex gap-3 border-t border-slate-200 pt-5"><Clock3 size={17} className="shrink-0 text-blue-700" /><div><p className="text-xs font-semibold text-slate-800">SLA</p><p className="mt-1 text-sm text-slate-600">{formatServiceSla(service.sla_hours)}</p></div></div></aside>
      </div>
    </section>
  </main>;
}

export default function CatalogCategoryPage() {
  return <Suspense fallback={<main className="mx-auto max-w-5xl py-10 text-sm text-slate-500">Đang tải dịch vụ...</main>}><CategoryContent /></Suspense>;
}
