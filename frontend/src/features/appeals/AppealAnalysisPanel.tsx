import { Badge, Card, Group, List, Progress, Stack, Text, Title } from '@mantine/core';
import { IconRoute } from '@tabler/icons-react';
import type { AppealAnalysis } from '@/shared/api';
import { formatPercent } from '@/shared/lib/format';
import { AppealCategoryBadge } from './AppealBadges';

export function AppealAnalysisPanel({ analysis }: { analysis: AppealAnalysis }) {
  return (
    <Card>
      <Stack gap="sm">
        <Title order={4}>Анализ</Title>
        <Group gap="xs">
          <Badge color={analysis.is_corruption ? 'red' : 'green'} variant="filled">
            {analysis.is_corruption ? 'Признаки коррупции' : 'Без признаков коррупции'}
          </Badge>
          <AppealCategoryBadge category={analysis.category} />
        </Group>

        <div>
          <Text size="xs" c="dimmed">
            Уверенность модели: {formatPercent(analysis.confidence)}
          </Text>
          <Progress value={analysis.confidence * 100} size="sm" />
        </div>
        <div>
          <Text size="xs" c="dimmed">
            Конкретность сообщения: {formatPercent(analysis.specificity)}
          </Text>
          <Progress value={analysis.specificity * 100} size="sm" color="orange" />
        </div>

        <Text size="sm">{analysis.summary}</Text>

        <div>
          <Text size="sm" fw={600} mb={4}>
            Сигналы
          </Text>
          {analysis.signals.length ? (
            <List size="sm" spacing={2}>
              {analysis.signals.map((s) => (
                <List.Item key={s.code}>{s.text}</List.Item>
              ))}
            </List>
          ) : (
            <Text size="sm" c="dimmed">
              нет
            </Text>
          )}
        </div>

        <Group gap={6} wrap="nowrap" align="flex-start">
          <IconRoute size={18} />
          <div>
            <Text size="xs" c="dimmed">
              Маршрут
            </Text>
            <Text size="sm" fw={500}>
              {analysis.route_to}
            </Text>
          </div>
        </Group>
      </Stack>
    </Card>
  );
}
