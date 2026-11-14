import { Alert, Anchor, Button, Card, Grid, Group, Stack, Text, Title } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { Link, useParams } from 'react-router';
import { AppealAnalysisPanel } from '@/features/appeals/AppealAnalysisPanel';
import { AppealStatusBadge } from '@/features/appeals/AppealBadges';
import { EntityLegend } from '@/features/appeals/EntityLegend';
import { HighlightedText } from '@/features/appeals/HighlightedText';
import { useAppeal, useReanalyzeAppeal } from '@/features/appeals/api';
import { LinkedOfficialPreview } from '@/features/appeals/LinkedOfficialPreview';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';
import { QueryState } from '@/shared/ui';

function LinkedOfficials({ persons }: { persons: string[] }) {
  return (
    <Card>
      <Title order={4} mb="sm">
        Связанные служащие
      </Title>
      {persons.length === 0 ? (
        <Text size="sm" c="dimmed">
          Не сопоставлены с базой служащих
        </Text>
      ) : (
        <Stack gap="sm">
          {persons.map((id) => (
            <LinkedOfficialPreview key={id} id={id} />
          ))}
        </Stack>
      )}
    </Card>
  );
}

export function AppealPage() {
  const { id = '' } = useParams();
  const appeal = useAppeal(id);
  const reanalyze = useReanalyzeAppeal();

  return (
    <>
      <Anchor component={Link} to={routes.appeals()} size="sm" mb="sm" display="inline-block">
        ← К обращениям
      </Anchor>
      <QueryState query={appeal}>
        {(a) => (
          <>
            <Group justify="space-between" mb="lg" wrap="wrap">
              <Stack gap={4}>
                <Title order={2}>Обращение от {formatDateTime(a.received_at)}</Title>
                <Group gap="xs">
                  <AppealStatusBadge status={a.status} />
                  <Text size="sm" c="dimmed">
                    {APPEAL_CHANNEL_LABELS[a.channel]}
                  </Text>
                </Group>
              </Stack>
              <Button
                variant="light"
                leftSection={<IconRefresh size={16} />}
                loading={reanalyze.isPending}
                onClick={() => reanalyze.mutate(a.id)}
              >
                Повторить анализ
              </Button>
            </Group>
            {reanalyze.isError && (
              <Alert color="red" mb="md" title="Не удалось повторить анализ">
                {reanalyze.error.message}
              </Alert>
            )}
            {reanalyze.isPending && (
              <Alert role="status" mb="md">
                Повторный анализ обычно занимает 5–15 секунд.
              </Alert>
            )}

            <Grid gutter="lg">
              <Grid.Col span={{ base: 12, md: 7 }}>
                <Stack>
                  <Card>
                    <Title order={4} mb="sm">
                      Текст
                    </Title>
                    <HighlightedText text={a.text} entities={a.analysis?.entities ?? []} />
                    {a.analysis && a.analysis.entities.length > 0 && (
                      <Stack gap={4} mt="md">
                        <Text size="xs" c="dimmed">
                          Найденные сущности:
                        </Text>
                        <EntityLegend />
                      </Stack>
                    )}
                  </Card>
                  <LinkedOfficials persons={a.linked_person_ids} />
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 5 }}>
                {a.analysis ? (
                  <AppealAnalysisPanel analysis={a.analysis} />
                ) : (
                  <Alert color="blue" title="Обращение ещё не проанализировано">
                    Нажмите «Повторить анализ», чтобы запустить классификацию.
                  </Alert>
                )}
              </Grid.Col>
            </Grid>
          </>
        )}
      </QueryState>
    </>
  );
}
