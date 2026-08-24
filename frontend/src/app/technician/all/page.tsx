import { redirect } from 'next/navigation';

/**
 * The queue is the single operational surface for incidents.  Keep this
 * redirect for old bookmarks without maintaining a second, inconsistent list.
 */
export default function LegacyTechnicianAllPage() {
  redirect('/technician/queue');
}
