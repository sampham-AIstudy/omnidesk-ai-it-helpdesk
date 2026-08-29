import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const protectedPages = [
  'src/app/admin/ai-console/page.tsx',
  'src/app/admin/ai-review/page.tsx',
  'src/app/admin/cmdb/page.tsx',
  'src/app/admin/integrations/page.tsx',
  'src/app/technician/alerts/page.tsx',
  'src/app/technician/on-call/page.tsx',
];

for (const relativePath of protectedPages) {
  const source = readFileSync(resolve(root, relativePath), 'utf8');
  if (/\btoast\.(?:success|error)\b|\bMOCK_[A-Z_]+\b/.test(source)) {
    throw new Error(`${relativePath} reintroduced a local mock mutation or success toast.`);
  }
}

const fulfillmentRoutes = [
  'src/app/technician/requests/page.tsx',
  'src/app/technician/requests/[id]/page.tsx',
];
for (const relativePath of fulfillmentRoutes) {
  const source = readFileSync(resolve(root, relativePath), 'utf8');
  if (!source.includes("from '@/lib/api'") || /\bMOCK_[A-Z_]+\b|toast\.(?:success|error)|safe-disabled|chưa khả dụng/.test(source)) {
    throw new Error(`${relativePath} must stay API-backed and must not regress to a local-only fulfillment UI.`);
  }
}

const statusSource = readFileSync(resolve(root, 'src/app/status/page.tsx'), 'utf8');
if (/All Systems Operational|99\.9\d*%|Operational'/.test(statusSource)) {
  throw new Error('Public status page reintroduced an unverified operational-health claim.');
}

const packageJson = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
if (packageJson.scripts.dev !== 'next dev --webpack' || packageJson.scripts.build !== 'next build --webpack') {
  throw new Error('Webpack must remain the explicit Next.js dev/build runtime on this environment.');
}

console.log(`Product guard checks passed for ${protectedPages.length} guarded routes and ${fulfillmentRoutes.length} API-backed fulfillment routes.`);
