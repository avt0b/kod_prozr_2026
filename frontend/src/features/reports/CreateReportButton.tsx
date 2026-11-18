import { Button } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconFileText } from '@tabler/icons-react';
import { useNavigate } from 'react-router';
import { routes } from '@/shared/config/routes';
import { useCreateReport } from './api';

export function CreateReportButton({
  personId,
  compact = false,
}: {
  personId: string;
  compact?: boolean;
}) {
  const navigate = useNavigate();
  const create = useCreateReport();
  return (
    <Button
      leftSection={<IconFileText size={18} />}
      loading={create.isPending}
      aria-label={compact ? 'Сформировать докладную' : undefined}
      onClick={() =>
        create.mutate(personId, {
          onSuccess: (report) => navigate(routes.report(report.id)),
          onError: (e) =>
            notifications.show({
              color: 'red',
              title: 'Не удалось сформировать',
              message: e.message,
            }),
        })
      }
    >
      {compact ? (
        <>
          <span className="workspace-report-label">Сформировать докладную</span>
          <span className="workspace-report-label-compact" aria-hidden>
            Докладная
          </span>
        </>
      ) : (
        'Сформировать докладную'
      )}
    </Button>
  );
}
