import { useEffect, useLayoutEffect, useRef, useSyncExternalStore, type ReactNode } from 'react';
import { Center, Loader } from '@mantine/core';
import { Navigate, useLocation } from 'react-router';
import { getSnapshot, refreshSession, subscribe } from '@/shared/lib/authSession';
import { WorkbenchProvider } from '@/features/workbench/WorkbenchProvider';
import { useQueryClient } from '@tanstack/react-query';

export function AuthGate({ children }: { children: ReactNode }) {
  const { user, ready, principal } = useSyncExternalStore(subscribe, getSnapshot);
  const previousPrincipal = useRef(principal);
  const location = useLocation();
  const client = useQueryClient();
  useEffect(() => {
    if (!ready) void refreshSession();
  }, [ready]);
  useLayoutEffect(() => {
    if (ready && (!user || previousPrincipal.current !== principal)) {
      void client.cancelQueries();
      client.clear();
    }
    previousPrincipal.current = principal;
  }, [ready, user, principal, client]);
  if (!ready)
    return (
      <Center mih="100dvh" role="status" aria-label="Проверка сессии">
        <Loader />
      </Center>
    );
  if (!user)
    return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />;
  return (
    <WorkbenchProvider key={principal} userId={user.id}>
      {children}
    </WorkbenchProvider>
  );
}
