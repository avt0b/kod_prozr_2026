import { Table, Text, UnstyledButton } from '@mantine/core';
import type { AuthorityKind, OrganRisk, PositionRisk } from '@/shared/api';
import { AUTHORITY_LABELS } from '@/shared/lib/labels';
import { HeatValue } from './HeatValue';
import { buildAuthorityHeatmap, type RiskMetric } from './riskMapModel';

interface Props {
  items: PositionRisk[];
  organs: OrganRisk[];
  metric: RiskMetric;
  selected: { organId: string | null; authority: AuthorityKind | null };
  onSelect: (organId: string, authority: AuthorityKind) => void;
}

/** Тепловая карта «вид полномочия × орган». Клик по ячейке фильтрует таблицу должностей. */
export function AuthorityHeatmap({ items, organs, metric, selected, onSelect }: Props) {
  const rows = buildAuthorityHeatmap(items, organs);
  return (
    <Table.ScrollContainer minWidth={640}>
      <Table withColumnBorders verticalSpacing={6} layout="fixed">
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={200}>Полномочие</Table.Th>
            {organs.map((o) => (
              <Table.Th key={o.organ_id} ta="center">
                <Text size="sm" fw={600} lineClamp={2}>
                  {o.organ}
                </Text>
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={row.authority}>
              <Table.Td fw={500}>{AUTHORITY_LABELS[row.authority]}</Table.Td>
              {organs.map((o) => {
                const cell = row.cells[o.organ_id];
                if (!cell) {
                  return (
                    <Table.Td key={o.organ_id} ta="center">
                      <Text size="sm" c="dimmed">
                        —
                      </Text>
                    </Table.Td>
                  );
                }
                const active =
                  selected.organId === o.organ_id && selected.authority === row.authority;
                return (
                  <Table.Td
                    key={o.organ_id}
                    p={4}
                    style={{
                      outline: active ? '2px solid var(--mantine-primary-color-filled)' : undefined,
                      outlineOffset: -2,
                    }}
                  >
                    <UnstyledButton
                      w="100%"
                      onClick={() => onSelect(o.organ_id, row.authority)}
                      aria-label={`${AUTHORITY_LABELS[row.authority]}: ${o.organ}`}
                    >
                      <HeatValue
                        agg={cell}
                        metric={metric}
                        caption={`${cell.officials_with_flags} из ${cell.officials_total} · ${cell.positions} должн.`}
                        tooltip={`Средний балл ${cell.avg_score}, максимальный ${cell.max_score}. С флагами ${cell.officials_with_flags} из ${cell.officials_total} служащих`}
                      />
                    </UnstyledButton>
                  </Table.Td>
                );
              })}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
