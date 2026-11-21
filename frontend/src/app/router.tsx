import { createBrowserRouter } from 'react-router';
import { AdminUsersPage } from '@/pages/admin-users/AdminUsersPage';
import { AppealNewPage } from '@/pages/appeal-new/AppealNewPage';
import { AppealPage } from '@/pages/appeal/AppealPage';
import { AppealsPage } from '@/pages/appeals/AppealsPage';
import { AssistantPage } from '@/pages/assistant/AssistantPage';
import { CitizenPage } from '@/pages/citizen/CitizenPage';
import { NotFoundPage } from '@/pages/not-found/NotFoundPage';
import { OfficialProfilePage } from '@/pages/official-profile/OfficialProfilePage';
import { OfficialsPage } from '@/pages/officials/OfficialsPage';
import { OverviewPage } from '@/pages/overview/OverviewPage';
import { ReportPage } from '@/pages/report/ReportPage';
import { RiskMapPage } from '@/pages/risk-map/RiskMapPage';
import { AppLayout } from './layout/AppLayout';
import { AuthGate } from '@/features/auth/AuthGate';
import { LoginPage } from '@/features/auth/LoginPage';
import { RoleGate } from '@/features/auth/RoleGate';
import { STAFF_ROLES } from '@/shared/lib/authSession';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/citizen',
    element: (
      <AuthGate roles={['citizen']} workbench={false}>
        <CitizenPage />
      </AuthGate>
    ),
  },
  {
    element: (
      <AuthGate roles={STAFF_ROLES}>
        <AppLayout />
      </AuthGate>
    ),
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'officials', element: <OfficialsPage /> },
      { path: 'officials/:id', element: <OfficialProfilePage /> },
      { path: 'risk-map', element: <RiskMapPage /> },
      { path: 'appeals', element: <AppealsPage /> },
      { path: 'appeals/new', element: <AppealNewPage /> },
      { path: 'appeals/:id', element: <AppealPage /> },
      { path: 'reports/:id', element: <ReportPage /> },
      { path: 'assistant', element: <AssistantPage /> },
      {
        path: 'admin/users',
        element: (
          <RoleGate roles={['admin']}>
            <AdminUsersPage />
          </RoleGate>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
