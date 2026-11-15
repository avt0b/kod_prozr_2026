import {
  Anchor,
  Badge,
  Button,
  Card,
  Divider,
  Drawer,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconListNumbers } from '@tabler/icons-react';
import { Link } from 'react-router';
import type { PositionRisk } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import {
  AUTHORITY_LABELS,
  RULE_TITLES,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '@/shared/lib/labels';
import { RiskScoreBadge } from '@/shared/ui';
import { ratingLink } from './links';
import { formatMetric } from './riskMapModel';

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={700} size="lg">
        {value}
      </Text>
    </Stack>
  );
}

interface Props {
  position: PositionRisk | null;
  onClose: () => void;
}

export function PositionRiskDrawer({ position, onClose }: Props) {
  return (
    <Drawer
      opened={position !== null}
      onClose={onClose}
      position="right"
      size="lg"
      title={<Text fw={600}>Карта рисков должности</Text>}
    >
      {position && (
        <Stack gap="md">
          <Stack gap={4}>
            <Title order={3}>{position.title}</Title>
            <Text size="sm" c="dimmed">
              {position.department} · {position.organ}
            </Text>
            <Group gap={6}>
              <Badge color={SEVERITY_COLORS[position.risk_level]} variant="light">
                риск должности: {SEVERITY_LABELS[position.risk_level]}
              </Badge>
              {position.is_corruption_risky && (
                <Badge color="grape" variant="light">
                  в перечне коррупционно-опасных
                </Badge>
              )}
              {position.authorities.map((a) => (
                <Badge key={a} variant="outline" color="gray">
                  {AUTHORITY_LABELS[a]}
                </Badge>
              ))}
            </Group>
          </Stack>

          <SimpleGrid cols={4}>
            <Metric label="Служащих" value={position.officials_total} />
            <Metric label="С флагами" value={formatMetric(position, 'flagged_share')} />
            <Metric label="Средний балл" value={formatMetric(position, 'avg_score')} />
            <Metric label="Макс. балл" value={formatMetric(position, 'max_score')} />
          </SimpleGrid>

          <Divider label="Типовые коррупционные риски по полномочиям" labelPosition="left" />
          {position.typical_risks.length === 0 && (
            <Text size="sm" c="dimmed">
              У должности нет полномочий из перечня: типовых рисков нет.
            </Text>
          )}
          {position.typical_risks.map((risk) => (
            <Card key={risk.code} withBorder p="sm">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Text fw={600} size="sm">
                  {risk.title}
                </Text>
                <Badge variant="outline" color="gray" size="sm" style={{ flexShrink: 0 }}>
                  {AUTHORITY_LABELS[risk.authority]}
                </Badge>
              </Group>
              <Text size="sm" mt={4}>
                {risk.description}
              </Text>
              <Group gap={6} mt={6}>
                {risk.rule_codes.length === 0 ? (
                  <Text size="xs" c="dimmed">
                    Система этот риск не проверяет — нужна ручная проверка.
                  </Text>
                ) : (
                  risk.rule_codes.map((code) => (
                    <Badge
                      key={code}
                      component={Link}
                      to={ratingLink(position.organ_id, code)}
                      variant="light"
                      radius="sm"
                      style={{ cursor: 'pointer' }}
                      title={RULE_TITLES[code]}
                    >
                      {code}
                    </Badge>
                  ))
                )}
                <Text size="xs" c="dimmed">
                  {risk.legal_ref}
                </Text>
              </Group>
            </Card>
          ))}

          <Divider label="Служащие с наибольшим риском" labelPosition="left" />
          {position.top_officials.length === 0 ? (
            <Text size="sm" c="dimmed">
              У служащих на этой должности флагов риска нет.
            </Text>
          ) : (
            <Stack gap={6}>
              {position.top_officials.map((o) => (
                <Group key={o.id} gap="sm">
                  <RiskScoreBadge score={o.risk_score} />
                  <Anchor component={Link} to={routes.official(o.id)} size="sm">
                    {o.full_name}
                  </Anchor>
                </Group>
              ))}
            </Stack>
          )}
          {position.top_rules.length > 0 && (
            <Group gap={6}>
              <Text size="sm" c="dimmed">
                Частые правила:
              </Text>
              {position.top_rules.map((r) => (
                <Badge
                  key={r.rule_code}
                  component={Link}
                  to={ratingLink(position.organ_id, r.rule_code)}
                  variant="light"
                  color="gray"
                  radius="sm"
                  style={{ cursor: 'pointer' }}
                  title={RULE_TITLES[r.rule_code]}
                >
                  {r.rule_code} × {r.count}
                </Badge>
              ))}
            </Group>
          )}

          <Button
            component={Link}
            to={ratingLink(position.organ_id)}
            variant="light"
            leftSection={<IconListNumbers size={16} />}
            style={{ alignSelf: 'flex-start' }}
          >
            Рейтинг служащих органа
          </Button>
          <Text size="xs" c="dimmed">
            Риск должности — свойство полномочий, а не вывод о служащем. Решение о проверке
            принимает аналитик.
          </Text>
        </Stack>
      )}
    </Drawer>
  );
}
