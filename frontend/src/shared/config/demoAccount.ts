import type { Role } from '../lib/roles';

/** Public credentials for the test stand, deliberately committed to Git. */
const PASSWORD = 'Demo-2026-Access!';
export const DEMO_ACCOUNTS: Record<Role, { username: string; password: string }> = {
  citizen: { username: 'demo-citizen', password: PASSWORD },
  analyst: { username: 'demo', password: PASSWORD },
  admin: { username: 'demo-admin', password: PASSWORD },
};
export const DEMO_ACCOUNT = DEMO_ACCOUNTS.analyst;
