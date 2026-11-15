import { Badge, Group, Table, Text, Tooltip } from '@mantine/core';
import type { PositionRisk } from '@/shared/api';
import {
  AUTHORITY_LABELS,
  RULE_TITLES,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '@/shared/lib/labels';
import { RiskScoreBadge } from '@/shared/ui';
import { HeatValue } from './HeatValue';
import { METRIC_LABELS, type RiskMetric } from './riskMapModel';

interface Props {
  items: PositionRisk[];
  metric: RiskMetric;
  onOpen: (position: PositionRisk) => void;
}

export function PositionRiskTable({ items, metric, onOpen }: Props) {
  return (
    <Table.ScrollContainer minWidth={1000}>
      <Table highlightOnHover verticalSpacing="xs">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Должность</Table.Th>
            <Table.Th>Орган</Table.Th>
            <Table.Th>Полномочия</Table.Th>
            <Table.Th>
              <Tooltip
                label="Свойство должности: зависит только от полномочий, не от людей"
                withArrow
              >
                <span>Риск должности</span>
              </Tooltip>
            </Table.Th>
            <Table.Th ta="center" w={120}>
              С флагами / всего
            </Table.Th>
            <Table.Th ta="center" w={130}>
              {METRIC_LABELS[metric]}
            </Table.Th>
            <Table.Th ta="center" w={90}>
              Макс. балл
            </Table.Th>
            <Table.Th>Частые правила</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((p) => (
            <Table.Tr
              key={p.position_id}
              style={{ cursor: 'pointer' }}
              onClick={() => onOpen(p)}
              aria-label={`Должность: ${p.title}`}
            >
              <Table.Td>
                <Text size="sm" fw={500}>
                  {p.title}
                </Text>
                <Text size="xs" c="dimmed">
                  {p.department}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" lineClamp={2}>
                  {p.organ}
                </Text>
              </Table.Td>
              <Table.Td>
                <Group gap={4}>
                  {p.authorities.length === 0 && (
                    <Text size="xs" c="dimmed">
                      нет
                    </Text>
                  )}
                  {p.authorities.map((a) => (
                    <Badge key={a} variant="outline" color="gray" radius="sm" size="sm">
                      {AUTHORITY_LABELS[a]}
                    </Badge>
                  ))}
                </Group>
              </Table.Td>
              <Table.Td>
                <Badge color={SEVERITY_COLORS[p.risk_level]} variant="light">
                  {SEVERITY_LABELS[p.risk_level]}
                </Badge>
              </Table.Td>
              <Table.Td ta="center">
                <Text size="sm">
                  {p.officials_with_flags} / {p.officials_total}
                </Text>
              </Table.Td>
              <Table.Td p={4}>
                <HeatValue agg={p} metric={metric} />
              </Table.Td>
              <Table.Td ta="center">
                <RiskScoreBadge score={p.max_score} />
              </Table.Td>
              <Table.Td>
                <Group gap={4}>
                  {p.top_rules.length === 0 && (
                    <Text size="xs" c="dimmed">
                      нет флагов
                    </Text>
                  )}
                  {p.top_rules.slice(0, 4).map((r) => (
                    <Tooltip key={r.rule_code} label={RULE_TITLES[r.rule_code]} withArrow>
                      <Badge variant="light" color="gray" radius="sm">
                        {r.rule_code} × {r.count}
                      </Badge>
                    </Tooltip>
                  ))}
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
