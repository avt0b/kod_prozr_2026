import { Anchor, Card, Grid, Stack, Text, Title } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { useOfficial } from '@/features/officials/api';
import { ReportActions, ReportView } from '@/features/reports/ReportView';
import { useReport } from '@/features/reports/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { PageHeader, QueryState } from '@/shared/ui';

function ReportSource({ personId }: { personId: string }) {
  const person = useOfficial(personId);
  return (
    <Card component="aside">
      <Stack gap="sm">
        <Title order={4}>Источник</Title>
        <Text size="sm" c="dimmed">
          Профиль служащего
        </Text>
        <Anchor component={Link} to={routes.official(personId)} size="sm">
          К профилю{person.data ? `: ${person.data.person.full_name}` : ''}
        </Anchor>
      </Stack>
    </Card>
  );
}

export function ReportPage() {
  const { id = '' } = useParams();
  const report = useReport(id);

  return (
    <QueryState query={report}>
      {(r) => (
        <>
          <PageHeader
            title="Докладная записка"
            description={`Черновик от ${formatDateTime(r.created_at)}. Проверьте текст перед отправкой.`}
            actions={<ReportActions text={r.text} />}
          />
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, lg: 9 }}>
              <ReportView report={r} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, lg: 3 }}>
              <ReportSource personId={r.person_id} />
            </Grid.Col>
          </Grid>
        </>
      )}
    </QueryState>
  );
}
