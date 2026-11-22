import { Alert, Anchor, Button, Card, Grid, Group, Stack, Text, Title } from '@mantine/core';
import { IconCircleCheck, IconRefresh, IconSend } from '@tabler/icons-react';
import { Link, useParams } from 'react-router';
import { AppealAnalysisPanel } from '@/features/appeals/AppealAnalysisPanel';
import { AppealStatusBadge } from '@/features/appeals/AppealBadges';
import { EntityLegend } from '@/features/appeals/EntityLegend';
import { HighlightedText } from '@/features/appeals/HighlightedText';
import { useAppeal, useReanalyzeAppeal, useSetAppealStatus } from '@/features/appeals/api';
import { LinkedOfficialPreview } from '@/features/appeals/LinkedOfficialPreview';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';
import type { AppealCandidate } from '@/shared/api';
import { QueryState } from '@/shared/ui';

function LinkedOfficials({
  persons,
  candidates,
}: {
  persons: string[];
  candidates: AppealCandidate[];
}) {
  return (
    <Card>
      <Title order={4} mb="sm">
        Связанные служащие
      </Title>
      {persons.length === 0 ? (
        <Text size="sm" c="dimmed">
          {candidates.length
            ? 'Автоматически не привязаны: упоминание неоднозначно'
            : 'Не сопоставлены с базой служащих'}
        </Text>
      ) : (
        <Stack gap="sm">
          {persons.map((id) => (
            <LinkedOfficialPreview key={id} id={id} />
          ))}
        </Stack>
      )}
      {candidates.length > 0 && (
        <Stack gap={4} mt="md">
          <Text size="sm" fw={600}>
            Возможно (подтверждает аналитик):
          </Text>
          {candidates.map((c) => (
            <Group key={c.person_id} gap="xs">
              <Anchor component={Link} to={routes.official(c.person_id)} size="sm">
                {c.full_name}
              </Anchor>
              <Text size="xs" c="dimmed">
                совпадение {Math.round(c.score * 100)}%
              </Text>
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
  const setStatus = useSetAppealStatus();

  return (
    <>
      <Anchor component={Link} to={routes.appeals()} size="sm" mb="sm" display="inline-block">
        ← К обращениям
      </Anchor>
      <QueryState query={appeal}>
        {(a) => (
          <>
            <Group className="workspace-page-heading" justify="space-between" mb="lg" wrap="wrap">
              <Stack gap={4}>
                <Title order={2}>Обращение от {formatDateTime(a.received_at)}</Title>
                <Group gap="xs">
                  <AppealStatusBadge status={a.status} />
                  <Text size="sm" c="dimmed">
                    {APPEAL_CHANNEL_LABELS[a.channel]}
                  </Text>
                </Group>
              </Stack>
              <Group gap="xs">
                {a.status === 'analyzed' && (
                  <Button
                    variant="light"
                    leftSection={<IconSend size={16} />}
                    loading={setStatus.isPending && setStatus.variables?.status === 'routed'}
                    disabled={setStatus.isPending}
                    onClick={() => setStatus.mutate({ id: a.id, status: 'routed' })}
                  >
                    Передать по подведомственности
                  </Button>
                )}
                {a.status !== 'closed' && (
                  <Button
                    variant="light"
                    color="gray"
                    leftSection={<IconCircleCheck size={16} />}
                    loading={setStatus.isPending && setStatus.variables?.status === 'closed'}
                    disabled={setStatus.isPending}
                    onClick={() => setStatus.mutate({ id: a.id, status: 'closed' })}
                  >
                    Закрыть
                  </Button>
                )}
                {a.status !== 'closed' && (
                  <Button
                    variant="light"
                    leftSection={<IconRefresh size={16} />}
                    loading={reanalyze.isPending}
                    onClick={() => reanalyze.mutate(a.id)}
                  >
                    {a.analysis ? 'Повторить анализ' : 'Запустить анализ'}
                  </Button>
                )}
              </Group>
            </Group>
            {setStatus.isError && (
              <Alert color="red" mb="md" title="Не удалось сменить статус">
                {setStatus.error.message}
              </Alert>
            )}
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
                  <LinkedOfficials
                    persons={a.linked_person_ids}
                    candidates={a.analysis?.candidates ?? []}
                  />
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 5 }}>
                {a.analysis ? (
                  <AppealAnalysisPanel analysis={a.analysis} />
                ) : (
                  <Alert color="blue" title="Обращение ещё не проанализировано">
                    Нажмите «Запустить анализ», чтобы классифицировать обращение.
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
