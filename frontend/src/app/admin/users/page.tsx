'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { PageHeader, Spinner } from '@/components/ui';
import { COMPANY_LABELS, ROLE_LABELS, formatRelative } from '@/lib/utils';
import { User } from '@/types';
import api from '@/lib/api';

type UserUpdate = Pick<User, 'full_name' | 'email' | 'phone' | 'role' | 'company_unit' | 'department' | 'is_vip'> & { is_active?: boolean };
type FulfillmentMembership = { technician_id: number; fulfillment_groups: string[] };
const roles = ['employee', 'technician', 'admin'] as const;
const units = ['real_estate', 'automotive', 'healthcare', 'corporate'] as const;
const errorMessage = (error: unknown) => (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Unable to save changes. No server state was changed.';

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<User | null>(null);
  const [confirming, setConfirming] = useState<User | null>(null);
  const [membershipUser, setMembershipUser] = useState<User | null>(null);
  const [membershipDraft, setMembershipDraft] = useState<string[] | null>(null);
  const [error, setError] = useState('');
  const { data, isLoading, isError } = useQuery({ queryKey: ['admin-users'], queryFn: async () => (await api.get('/admin/users')).data as User[] });
  const { data: availableGroups = [] } = useQuery({ queryKey: ['fulfillment-groups'], queryFn: async () => (await api.get('/admin/fulfillment-groups')).data.items as string[] });
  const { data: membership, isLoading: loadingMembership } = useQuery({
    queryKey: ['technician-fulfillment-groups', membershipUser?.id],
    queryFn: async () => (await api.get(`/admin/technicians/${membershipUser?.id}/fulfillment-groups`)).data as FulfillmentMembership,
    enabled: membershipUser?.role === 'technician',
  });
  const update = useMutation({
    mutationFn: async ({ id, changes }: { id: number; changes: Partial<UserUpdate> }) => (await api.patch(`/admin/users/${id}`, changes)).data as User,
    onSuccess: () => { setError(''); setEditing(null); setConfirming(null); void queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: (caught) => setError(errorMessage(caught)),
  });
  const updateMembership = useMutation({
    mutationFn: async ({ id, fulfillment_groups }: { id: number; fulfillment_groups: string[] }) => (await api.put(`/admin/technicians/${id}/fulfillment-groups`, { fulfillment_groups })).data as FulfillmentMembership,
    onSuccess: () => { setError(''); setMembershipUser(null); setMembershipDraft(null); void queryClient.invalidateQueries({ queryKey: ['technician-fulfillment-groups'] }); },
    onError: (caught) => setError(errorMessage(caught)),
  });
  const users = data ?? [];
  const selectedGroups = membershipDraft ?? membership?.fulfillment_groups ?? [];
  const toggleGroup = (group: string) => setMembershipDraft((draft) => {
    const current = draft ?? membership?.fulfillment_groups ?? [];
    return current.includes(group) ? current.filter((item) => item !== group) : [...current, group].sort();
  });
  const saveUser = () => editing && update.mutate({ id: editing.id, changes: {
    full_name: editing.full_name, email: editing.email, phone: editing.phone ?? null, role: editing.role,
    company_unit: editing.company_unit, department: editing.department ?? null, is_vip: editing.is_vip,
  } });

  return <div>
    <PageHeader title="User management" subtitle={`${users.length} accounts`} />
    {error && <div role="alert" className="mb-4 rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
    {isLoading ? <div className="flex justify-center p-16"><Spinner size={36} /></div> : isError ? <div role="alert" className="glass-card p-5 text-sm text-red-200">Unable to load users.</div> : <div className="glass-card overflow-x-auto p-0"><table className="data-table"><thead><tr><th>ID</th><th>Name</th><th>Role</th><th>Company</th><th>Status</th><th>Created</th><th>Fulfillment groups</th><th>Actions</th></tr></thead><tbody>
      {users.map((user) => <tr key={user.id}><td>#{user.id}</td><td><div className="font-semibold">{user.full_name}</div><div className="text-xs text-[var(--text-muted)]">{user.username} · {user.email}</div></td><td>{ROLE_LABELS[user.role]}</td><td>{COMPANY_LABELS[user.company_unit] ?? user.company_unit}</td><td className={user.is_active ? 'text-emerald-400' : 'text-rose-400'}>{user.is_active ? 'Active' : 'Inactive'}</td><td>{formatRelative(user.created_at)}</td><td>{user.role === 'technician' ? <button type="button" className="btn-ghost px-2 py-1 text-xs" disabled={updateMembership.isPending} onClick={() => { setError(''); setMembershipDraft(null); setMembershipUser(user); }}>Configure</button> : '-'}</td><td><div className="flex gap-2"><button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => { setError(''); setEditing({ ...user }); }}>Edit</button><button type="button" className="btn-ghost px-2 py-1 text-xs" disabled={update.isPending} onClick={() => { setError(''); setConfirming(user); }}>{user.is_active ? 'Deactivate' : 'Reactivate'}</button></div></td></tr>)}
    </tbody></table></div>}
    {editing && <Modal title={`Edit ${editing.username}`}><div className="grid gap-3 sm:grid-cols-2"><Input label="Name" value={editing.full_name} onChange={(full_name) => setEditing({ ...editing, full_name })} /><Input label="Email" value={editing.email} onChange={(email) => setEditing({ ...editing, email })} /><Input label="Phone" value={editing.phone ?? ''} onChange={(phone) => setEditing({ ...editing, phone: phone || null })} /><Input label="Department" value={editing.department ?? ''} onChange={(department) => setEditing({ ...editing, department: department || null })} /><label className="text-sm">Role<select className="mt-1 w-full rounded border p-2" value={editing.role} onChange={(event) => setEditing({ ...editing, role: event.target.value as User['role'] })}>{roles.map((role) => <option key={role} value={role}>{ROLE_LABELS[role]}</option>)}</select></label><label className="text-sm">Company<select className="mt-1 w-full rounded border p-2" value={editing.company_unit} onChange={(event) => setEditing({ ...editing, company_unit: event.target.value as User['company_unit'] })}>{units.map((unit) => <option key={unit} value={unit}>{COMPANY_LABELS[unit]}</option>)}</select></label></div><Actions pending={update.isPending} onCancel={() => setEditing(null)} onSave={saveUser} /></Modal>}
    {confirming && <Modal title={`${confirming.is_active ? 'Deactivate' : 'Reactivate'} account?`}><p className="text-sm text-[var(--text-muted)]">{confirming.is_active ? 'Existing tokens are rejected after confirmation.' : 'The user can sign in again after confirmation.'}</p><Actions pending={update.isPending} onCancel={() => setConfirming(null)} onSave={() => update.mutate({ id: confirming.id, changes: { is_active: !confirming.is_active } })} saveLabel="Confirm" /></Modal>}
    {membershipUser && <Modal title={`Fulfillment groups: ${membershipUser.username}`}><p className="text-sm text-[var(--text-muted)]">An empty membership cannot see or take new Service Requests.</p>{loadingMembership ? <div className="flex justify-center p-8"><Spinner size={28} /></div> : <fieldset className="mt-5 grid gap-2 sm:grid-cols-2">{availableGroups.map((group) => <label key={group} className="flex items-center gap-2 rounded border p-2 text-sm"><input type="checkbox" checked={selectedGroups.includes(group)} disabled={updateMembership.isPending} onChange={() => toggleGroup(group)} />{group}</label>)}</fieldset>}<Actions pending={updateMembership.isPending} disabled={loadingMembership} onCancel={() => { setMembershipUser(null); setMembershipDraft(null); }} onSave={() => updateMembership.mutate({ id: membershipUser.id, fulfillment_groups: selectedGroups })} saveLabel="Save groups" /></Modal>}
  </div>;
}

function Modal({ title, children }: { title: string; children: React.ReactNode }) { return <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4"><section role="dialog" aria-modal="true" className="glass-card w-full max-w-xl p-6"><h2 className="text-lg font-semibold">{title}</h2><div className="mt-5">{children}</div></section></div>; }
function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="text-sm">{label}<input className="mt-1 w-full rounded border p-2" value={value} onChange={(event) => onChange(event.target.value)} /></label>; }
function Actions({ pending, disabled = false, onCancel, onSave, saveLabel = 'Save changes' }: { pending: boolean; disabled?: boolean; onCancel: () => void; onSave: () => void; saveLabel?: string }) { return <div className="mt-6 flex justify-end gap-3"><button type="button" className="btn-ghost" disabled={pending} onClick={onCancel}>Cancel</button><button type="button" className="btn-primary" disabled={disabled || pending} onClick={onSave}>{pending ? 'Saving...' : saveLabel}</button></div>; }
