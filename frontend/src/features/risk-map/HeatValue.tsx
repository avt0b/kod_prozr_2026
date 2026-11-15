import { Box, Stack, Text, Tooltip } from '@mantine/core';
import type { ReactNode } from 'react';
import {
  formatMetric,
  heatBackground,
  heatTextColor,
  metricIntensity,
  type HeatCell,
  type RiskMetric,
} from './riskMapModel';

interface Props {
  agg: Pick<HeatCell, RiskMetric | 'officials_total' | 'officials_with_flags'>;
  metric: RiskMetric;
  caption?: ReactNode;
  tooltip?: ReactNode;
}

/** Окрашенная ячейка: значение метрики крупно, подпись мелко. */
export function HeatValue({ agg, metric, caption, tooltip }: Props) {
  const intensity = metricIntensity(agg, metric);
  const color = heatTextColor(intensity);
  const body = (
    <Box
      px="xs"
      py={6}
      style={{
        background: heatBackground(intensity),
        borderRadius: 'var(--mantine-radius-sm)',
        color,
      }}
    >
      <Stack gap={0} align="center">
        <Text fw={700} size="md" c={color ? 'inherit' : undefined}>
          {formatMetric(agg, metric)}
        </Text>
        {caption && (
          <Text size="xs" c={color ? 'inherit' : 'dimmed'} style={{ whiteSpace: 'nowrap' }}>
            {caption}
          </Text>
        )}
      </Stack>
    </Box>
  );
  return tooltip ? (
    <Tooltip label={tooltip} withArrow multiline maw={280}>
      {body}
    </Tooltip>
  ) : (
    body
  );
}
