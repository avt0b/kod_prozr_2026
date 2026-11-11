import { Group, Text } from '@mantine/core';
import type { GraphNodeType } from '@/shared/api';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';
import { NODE_STYLES } from './graphStyle';

const SHAPE_RADIUS: Record<string, string> = { ellipse: '50%', 'round-rectangle': '3px' };

export function GraphLegend() {
  return (
    <Group gap="md">
      {(Object.keys(NODE_STYLES) as GraphNodeType[]).map((type) => (
        <Group key={type} gap={6}>
          <span
            style={{
              width: 12,
              height: 12,
              display: 'inline-block',
              background: NODE_STYLES[type].color,
              borderRadius: SHAPE_RADIUS[NODE_STYLES[type].shape] ?? 0,
              transform:
                NODE_STYLES[type].shape === 'diamond' ? 'rotate(45deg) scale(0.8)' : undefined,
            }}
          />
          <Text size="xs">{NODE_TYPE_LABELS[type]}</Text>
        </Group>
      ))}
      <Text size="xs" c="dimmed">
        Красная обводка — высокий риск. Пунктир — родство.
      </Text>
    </Group>
  );
}
