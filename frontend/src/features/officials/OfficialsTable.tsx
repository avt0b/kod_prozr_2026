import { Anchor, Group, Table, Text, UnstyledButton } from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconSelector } from '@tabler/icons-react';
import { Link, useLocation, useNavigate } from 'react-router';
import type { OfficialListItem, OfficialsSort } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { FlagBadge, RiskScoreBadge } from '@/shared/ui';
import { CaseActions } from '@/features/workbench/CaseActions';
import { useWorkbench } from '@/features/workbench/context';

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
    <UnstyledButton
      className="officials-sort"
      data-active={active || undefined}
      data-numeric={field === 'risk_score' || undefined}
      aria-label={`${label}: сортировать по ${next.startsWith('-') ? 'убыванию' : 'возрастанию'}`}
      onClick={() => onSortChange(next)}
    >
      <Group gap={4} wrap="nowrap">
        <Text fw={600} size="sm">
          {label}
        </Text>
        <Icon className="officials-sort-arrow" size={16} aria-hidden="true" />
      </Group>
    </UnstyledButton>
  );
}

export function OfficialsTable({ items, sort, onSortChange, startIndex = 0 }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const profileState =
    location.pathname === routes.officials() ? { ratingSearch: location.search } : undefined;
  const { state } = useWorkbench();
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table className="officials-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={40} ta="right">
              #
            </Table.Th>
            <Table.Th
              w={90}
              ta="right"
              aria-sort={
                sort?.replace('-', '') === 'risk_score'
                  ? sort.startsWith('-')
                    ? 'descending'
                    : 'ascending'
                  : undefined
              }
            >
              <SortHeader label="Балл" field="risk_score" sort={sort} onSortChange={onSortChange} />
            </Table.Th>
            <Table.Th
              aria-sort={
                sort?.replace('-', '') === 'full_name'
                  ? sort.startsWith('-')
                    ? 'descending'
                    : 'ascending'
                  : undefined
              }
            >
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
              data-compared={state.comparison.some((item) => item.id === o.id) || undefined}
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(routes.official(o.id), { state: profileState })}
            >
              <Table.Td c="dimmed" ta="right">
                {startIndex + i + 1}
              </Table.Td>
              <Table.Td ta="right">
                <RiskScoreBadge score={o.risk_score} />
              </Table.Td>
              <Table.Td fw={500}>
                <Anchor
                  className="official-name-link workspace-row-link"
                  component={Link}
                  to={routes.official(o.id)}
                  state={profileState}
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
