import { Alert, Anchor, Button, Card, Grid, Group, Stack, Text, Title } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { Link, useParams } from 'react-router';
import { AppealAnalysisPanel } from '@/features/appeals/AppealAnalysisPanel';
import { AppealStatusBadge } from '@/features/appeals/AppealBadges';
import { EntityLegend } from '@/features/appeals/EntityLegend';
import { HighlightedText } from '@/features/appeals/HighlightedText';
import { useAppeal, useReanalyzeAppeal } from '@/features/appeals/api';
import type { LinkedOfficial } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';
import { QueryState, RiskScoreBadge } from '@/shared/ui';

function LinkedOfficials({ persons }: { persons: LinkedOfficial[] }) {
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
          {persons.map((p) => (
            <Group key={p.id} wrap="nowrap" align="flex-start">
              <RiskScoreBadge score={p.risk_score} />
              <div>
                <Anchor component={Link} to={routes.official(p.id)} fw={500} size="sm">
                  {p.full_name}
                </Anchor>
                <Text size="xs" c="dimmed">
                  {p.position} · {p.organ}
                </Text>
              </div>
            </Group>
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
                  <LinkedOfficials persons={a.linked_persons} />
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
