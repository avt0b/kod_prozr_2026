import { Anchor, Stack } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { useOfficial } from '@/features/officials/api';
import { ReportView } from '@/features/reports/ReportView';
import { useReport } from '@/features/reports/api';
import { routes } from '@/shared/config/routes';
import { PageHeader, QueryState } from '@/shared/ui';

function ReportBackLink({ personId }: { personId: string }) {
  const person = useOfficial(personId);
  return (
    <Anchor component={Link} to={routes.official(personId)} size="sm">
      ← К профилю{person.data ? `: ${person.data.person.full_name}` : ''}
    </Anchor>
  );
}

export function ReportPage() {
  const { id = '' } = useParams();
  const report = useReport(id);

  return (
    <QueryState query={report}>
      {(r) => (
        <Stack gap={0} maw={900}>
          <ReportBackLink personId={r.person_id} />
          <PageHeader
            title="Докладная записка"
            description="Автоматически сформированный черновик. Проверьте и отредактируйте перед отправкой."
          />
          <ReportView report={r} />
        </Stack>
      )}
    </QueryState>
  );
}
