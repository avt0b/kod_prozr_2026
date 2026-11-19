import { Anchor, Group, Table, Text, UnstyledButton } from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconSelector } from '@tabler/icons-react';
import { Link, useNavigate } from 'react-router';
import type { OfficialListItem, OfficialsSort } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { FlagBadge, RiskScoreBadge } from '@/shared/ui';
import { CaseActions } from '@/features/workbench/CaseActions';

interface Props {
  items: OfficialListItem[];
  /** Если не передать — заголовки не сортируются (например, топ-10 на обзоре). */
  sort?: OfficialsSort;
  onSortChange?: (sort: OfficialsSort) => void;
  startIndex?: number;
}

function SortHeader({
  label,
  field,
  sort,
  onSortChange,
}: {
  label: string;
  field: 'risk_score' | 'full_name';
  sort?: OfficialsSort;
  onSortChange?: (s: OfficialsSort) => void;
}) {
  if (!sort || !onSortChange) return <>{label}</>;
  const active = sort.replace('-', '') === field;
  const desc = sort.startsWith('-');
  const Icon = !active ? IconSelector : desc ? IconArrowDown : IconArrowUp;
  const next: OfficialsSort = active && desc ? field : (`-${field}` as OfficialsSort);
  return (
    <UnstyledButton onClick={() => onSortChange(next)}>
      <Group gap={4} wrap="nowrap">
        <Text fw={600} size="sm">
          {label}
        </Text>
        <Icon size={14} />
      </Group>
    </UnstyledButton>
  );
}

export function OfficialsTable({ items, sort, onSortChange, startIndex = 0 }: Props) {
  const navigate = useNavigate();
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={40}>#</Table.Th>
            <Table.Th w={90}>
              <SortHeader label="Балл" field="risk_score" sort={sort} onSortChange={onSortChange} />
            </Table.Th>
            <Table.Th>
              <SortHeader label="ФИО" field="full_name" sort={sort} onSortChange={onSortChange} />
            </Table.Th>
            <Table.Th>Должность и орган</Table.Th>
            <Table.Th>Флаги</Table.Th>
            <Table.Th w={90}>Кейс</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((o, i) => (
            <Table.Tr
              key={o.id}
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(routes.official(o.id))}
            >
              <Table.Td c="dimmed">{startIndex + i + 1}</Table.Td>
              <Table.Td>
                <RiskScoreBadge score={o.risk_score} />
              </Table.Td>
              <Table.Td fw={500}>
                <Anchor
                  className="official-name-link"
                  component={Link}
                  to={routes.official(o.id)}
                  onClick={(event) => event.stopPropagation()}
                >
                  {o.full_name}
                </Anchor>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{o.position}</Text>
                <Text size="xs" c="dimmed">
                  {o.organ}
                </Text>
              </Table.Td>
              <Table.Td>
                <Group gap={4}>
                  {o.top_flags.length === 0 && (
                    <Text size="xs" c="dimmed">
                      нет
                    </Text>
                  )}
                  {o.top_flags.map((f) => (
                    <FlagBadge key={f.rule_code} ruleCode={f.rule_code} severity={f.severity} />
                  ))}
                </Group>
              </Table.Td>
              <Table.Td>
                <CaseActions person={{ id: o.id, name: o.full_name }} />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
