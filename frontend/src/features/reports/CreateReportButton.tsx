import { Button } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconFileText } from '@tabler/icons-react';
import { useNavigate } from 'react-router';
import { routes } from '@/shared/config/routes';
import { useCreateReport } from './api';

export function CreateReportButton({ personId }: { personId: string }) {
  const navigate = useNavigate();
  const create = useCreateReport();
  return (
    <Button
      leftSection={<IconFileText size={18} />}
      loading={create.isPending}
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
      Сформировать докладную
    </Button>
  );
}
