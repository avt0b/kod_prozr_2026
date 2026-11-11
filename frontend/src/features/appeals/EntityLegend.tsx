import { Group, Mark, Text } from '@mantine/core';
import type { EntityType } from '@/shared/api';
import { ENTITY_COLORS, ENTITY_LABELS } from '@/shared/lib/labels';

export function EntityLegend() {
  return (
    <Group gap="sm">
      {(Object.keys(ENTITY_LABELS) as EntityType[]).map((t) => (
        <Text key={t} size="xs">
          <Mark color={ENTITY_COLORS[t]} px={4}>
            {ENTITY_LABELS[t]}
          </Mark>
        </Text>
      ))}
    </Group>
  );
}
