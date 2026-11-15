import { createBrowserRouter } from 'react-router';
import { AppealNewPage } from '@/pages/appeal-new/AppealNewPage';
import { AppealPage } from '@/pages/appeal/AppealPage';
import { AppealsPage } from '@/pages/appeals/AppealsPage';
import { AssistantPage } from '@/pages/assistant/AssistantPage';
import { NotFoundPage } from '@/pages/not-found/NotFoundPage';
import { OfficialProfilePage } from '@/pages/official-profile/OfficialProfilePage';
import { OfficialsPage } from '@/pages/officials/OfficialsPage';
import { OverviewPage } from '@/pages/overview/OverviewPage';
import { ReportPage } from '@/pages/report/ReportPage';
import { RiskMapPage } from '@/pages/risk-map/RiskMapPage';
import { AppLayout } from './layout/AppLayout';

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
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
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
