import { useSyncExternalStore, type ReactNode } from 'react';
import { Navigate } from 'react-router';
import { getSnapshot, homeOf, subscribe, type Role } from '@/shared/lib/authSession';

/** Вложенный раздел для части ролей внутри уже проверенной AuthGate. */
export function RoleGate({ roles, children }: { roles: readonly Role[]; children: ReactNode }) {
  const { user } = useSyncExternalStore(subscribe, getSnapshot);
  if (!user) return null;
  if (!roles.includes(user.role)) return <Navigate to={homeOf(user.role)} replace />;
  return <>{children}</>;
}
