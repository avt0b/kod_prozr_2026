import { Badge, Card, Group, Stack, Text } from '@mantine/core';
import type { CSSProperties } from 'react';
import type { RiskFlag } from '@/shared/api';
import {
  NODE_TYPE_LABELS,
  RULE_TITLES,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '@/shared/lib/labels';

interface Props {
  flags: RiskFlag[];
  selectedId?: string | null;
  onSelect?: (flag: RiskFlag | null) => void;
}

/** Список флагов с объяснением, нормой права и цепочкой evidence. Клик выделяет флаг (повторный — снимает). */
export function FlagList({ flags, selectedId, onSelect }: Props) {
  if (!flags.length) {
    return (
      <Text c="dimmed" size="sm">
        Флагов риска не выявлено.
      </Text>
    );
  }
  return (
    <Stack gap="sm">
      {flags.map((f, index) => {
        const selected = f.id === selectedId;
        return (
          <Card
            key={f.id}
            padding="md"
            className="workspace-flag"
            style={{ '--motion-index': Math.min(index, 5) } as CSSProperties}
            data-selectable={onSelect ? '' : undefined}
            data-selected={selected ? '' : undefined}
            data-severity={f.severity}
            role={onSelect ? 'button' : undefined}
            tabIndex={onSelect ? 0 : undefined}
            aria-pressed={onSelect ? selected : undefined}
            onClick={() => onSelect?.(selected ? null : f)}
            onKeyDown={(event) => {
              if (onSelect && (event.key === 'Enter' || event.key === ' ')) {
                event.preventDefault();
                onSelect(selected ? null : f);
              }
            }}
          >
            <Group justify="space-between" mb={6} gap="xs" align="flex-start">
              <Group gap="xs">
                <Badge color={SEVERITY_COLORS[f.severity]} variant="filled">
                  {f.rule_code}
                </Badge>
                <Text fw={600}>{RULE_TITLES[f.rule_code]}</Text>
              </Group>
              <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                риск {SEVERITY_LABELS[f.severity]} · вес {f.weight}
              </Text>
            </Group>

            <dl className="flag-evidence-details">
              <div>
                <dt>Факт и пояснение</dt>
                <dd>{f.explanation}</dd>
              </div>
              <div>
                <dt>Записи-источники</dt>
                <dd>
                  {f.evidence.length ? (
                    <ol>
                      {f.evidence.map((e) => (
                        <li key={e.node_id}>
                          <span className="flag-source-type">{NODE_TYPE_LABELS[e.type]}</span>
                          <span title={e.node_id}>{e.label}</span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <Text size="sm" c="dimmed">
                      В данных не указаны
                    </Text>
                  )}
                </dd>
              </div>
              <div>
                <dt>Правовое основание</dt>
                <dd>
                  {f.legal_ref || (
                    <Text size="sm" c="dimmed">
                      В данных не указано
                    </Text>
                  )}
                </dd>
              </div>
            </dl>
          </Card>
        );
      })}
    </Stack>
  );
}
