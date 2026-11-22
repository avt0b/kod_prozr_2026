import { Anchor, Card } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link, useNavigate } from 'react-router';
import { AppealForm } from '@/features/appeals/AppealForm';
import { useCreateAppeal } from '@/features/appeals/api';
import { routes } from '@/shared/config/routes';
import { PageHeader } from '@/shared/ui';

export function AppealNewPage() {
  const navigate = useNavigate();
  const create = useCreateAppeal();

  return (
    <>
      <Anchor component={Link} to={routes.appeals()} size="sm" mb="sm" display="inline-block">
        ← К обращениям
      </Anchor>
      <PageHeader
        title="Новое обращение"
        description="Регистрация обращения гражданина и автоматический анализ текста"
      />
      <Card>
        <AppealForm
          submitting={create.isPending}
          onSubmit={(payload) =>
            create.mutate(payload, {
              onSuccess: (appeal) => {
                notifications.show({
                  color: 'teal',
                  message: 'Обращение зарегистрировано и проанализировано',
                });
                navigate(routes.appeal(appeal.id));
              },
              onError: (e) =>
                notifications.show({ color: 'red', title: 'Ошибка', message: e.message }),
            })
          }
        />
      </Card>
    </>
  );
}
