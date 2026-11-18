import { Badge, Card, Group, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconChevronRight, IconScale } from '@tabler/icons-react';
import { Fragment } from 'react';
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
      {flags.map((f) => {
        const selected = f.id === selectedId;
        return (
          <Card
            key={f.id}
            padding="md"
            className="workspace-flag"
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

            <Text size="sm">{f.explanation}</Text>

            {f.legal_ref && (
              <Group gap={6} mt="xs" wrap="nowrap" align="flex-start">
                <ThemeIcon size="sm" variant="light" color="gray">
                  <IconScale size={14} />
                </ThemeIcon>
                <Text size="xs" c="dimmed">
                  {f.legal_ref}
                </Text>
              </Group>
            )}

            {f.evidence.length > 0 && (
              <Group gap={4} mt="xs">
                <Text size="xs" c="dimmed">
                  Цепочка:
                </Text>
                {f.evidence.map((e, i) => (
                  <Fragment key={e.node_id}>
                    {i > 0 && <IconChevronRight size={12} />}
                    <Badge
                      size="sm"
                      variant="outline"
                      color="gray"
                      tt="none"
                      radius="sm"
                      fw={500}
                      h="auto"
                      py={2}
                      maw="100%"
                      title={`${NODE_TYPE_LABELS[e.type]}: ${e.label}`}
                      styles={{
                        label: { whiteSpace: 'normal', overflow: 'visible', textAlign: 'left' },
                      }}
                    >
                      {e.label}
                    </Badge>
                  </Fragment>
                ))}
              </Group>
            )}
          </Card>
        );
      })}
    </Stack>
  );
}
