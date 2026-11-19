import { Badge, Group, Table, Text, Title } from '@mantine/core';
import { IconCheck, IconMinus, IconArrowsDiff, IconCirclesRelation } from '@tabler/icons-react';
import type { OfficialProfile } from '@/shared/api';
import { RULE_TITLES, SEVERITY_LABELS } from '@/shared/lib/labels';
import { buildRuleMatrix, type RuleCell } from './ruleMatrix';
import type { CaseRef } from './model';

function shortName(name: string) {
  const [last, ...rest] = name.split(/\s+/);
  return [last, ...rest.map((part) => `${part[0]}.`)].join(' ');
}

function RuleMarker({ cell }: { cell: RuleCell | null }) {
  return cell ? (
    <span
      className="rule-presence"
      data-severity={cell.severity}
      aria-label={`Флаг выявлен: ${SEVERITY_LABELS[cell.severity]} риск, количество ${cell.count}`}
    >
      <IconCheck size={18} aria-hidden="true" />
      <span>
        {SEVERITY_LABELS[cell.severity]}
        {cell.count > 1 && ` · ${cell.count}`}
      </span>
    </span>
  ) : (
    <span className="rule-absence">
      <IconMinus size={18} aria-hidden="true" />
      Не выявлен
    </span>
  );
}

export function RuleComparison({
  cases,
  profiles,
}: {
  cases: CaseRef[];
  profiles: OfficialProfile[];
}) {
  const rows = buildRuleMatrix(profiles);
  const shared = rows.filter((row) => row.shared).length;
  return (
    <section className="rule-comparison" aria-label="Матрица сигналов риска">
      <Group justify="space-between" align="flex-start" gap="md">
        <div>
          <Title order={3}>Что совпадает, а что отличается</Title>
          <Text size="sm" c="dimmed" mt={6}>
            Общие правила выделены. В каждой ячейке — наличие и тяжесть сигнала.
          </Text>
        </div>
        <div className="rule-summary">
          <div>
            <IconCirclesRelation size={20} />
            <strong>{shared}</strong>
            <span>совпадают у всех</span>
          </div>
          <div>
            <IconArrowsDiff size={20} />
            <strong>{rows.length - shared}</strong>
            <span>есть не у всех</span>
          </div>
        </div>
      </Group>
      {rows.length ? (
        <>
          <div
            className="rule-matrix-scroll"
            tabIndex={0}
            role="region"
            aria-label="Таблица совпадений и различий, доступна горизонтальная прокрутка"
          >
            <Table
              className="rule-matrix"
              aria-label="Совпадения правил по служащим"
              highlightOnHover={false}
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Правило риска</Table.Th>
                  {cases.map((item) => (
                    <Table.Th key={item.id} aria-label={item.name}>
                      <span className="rule-person-initials" aria-hidden="true">
                        {item.name
                          .split(/\s+/)
                          .slice(0, 2)
                          .map((part) => part[0])
                          .join('')}
                      </span>
                      <span title={item.name}>{shortName(item.name)}</span>
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((row) => (
                  <Table.Tr key={row.code} data-shared={row.shared || undefined}>
                    <Table.Th scope="row">
                      <div className="rule-matrix-name">
                        <Badge variant={row.shared ? 'filled' : 'light'} size="sm">
                          {row.code}
                        </Badge>
                        <span>
                          {RULE_TITLES[row.code]}
                          {row.shared && <small>У всех выбранных</small>}
                        </span>
                      </div>
                    </Table.Th>
                    {row.cells.map((cell, index) => (
                      <Table.Td key={cases[index].id}>
                        <RuleMarker cell={cell} />
                      </Table.Td>
                    ))}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </div>
          <div className="rule-mobile-matrix" aria-label="Сигналы по служащим">
            {rows.map((row) => (
              <article
                className="rule-mobile-row"
                key={row.code}
                data-shared={row.shared || undefined}
              >
                <div className="rule-matrix-name">
                  <Badge variant={row.shared ? 'filled' : 'light'} size="sm">
                    {row.code}
                  </Badge>
                  <span>
                    {RULE_TITLES[row.code]}
                    {row.shared && <small>У всех выбранных</small>}
                  </span>
                </div>
                <div
                  className="rule-mobile-cases"
                  style={{ gridTemplateColumns: `repeat(${cases.length}, minmax(0, 1fr))` }}
                >
                  {row.cells.map((cell, index) => (
                    <div key={cases[index].id} role="group" aria-label={cases[index].name}>
                      <span className="rule-mobile-name" title={cases[index].name}>
                        {shortName(cases[index].name)}
                      </span>
                      <RuleMarker cell={cell} />
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      ) : (
        <Text c="dimmed" mt="lg">
          В выбранных профилях флагов риска не выявлено.
        </Text>
      )}
      <Text size="xs" c="dimmed" mt="md">
        Цвет обозначает тяжесть сигнала, отметка — его наличие. Совпадение правила само по себе не
        означает связь между служащими.
      </Text>
    </section>
  );
}
