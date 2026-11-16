import { Mark, Text, Tooltip } from '@mantine/core';
import type { ReactNode } from 'react';
import type { AppealEntity } from '@/shared/api';
import { ENTITY_COLORS, ENTITY_LABELS } from '@/shared/lib/labels';
import { entityRanges } from './entityRanges';

/** Подсвечивает сущности в тексте по смещениям start/end (пересекающиеся отбрасываются). */
export function HighlightedText({ text, entities }: { text: string; entities: AppealEntity[] }) {
  const parts: ReactNode[] = [];
  let cursor = 0;
  const sorted = entityRanges(text, entities);

  for (const e of sorted) {
    if (e.start < cursor || e.end > text.length || e.start >= e.end) continue;
    if (e.start > cursor) parts.push(text.slice(cursor, e.start));
    parts.push(
      <Tooltip key={`${e.start}-${e.end}`} label={ENTITY_LABELS[e.type]} withArrow>
        <Mark color={ENTITY_COLORS[e.type]} px={2} style={{ borderRadius: 3 }}>
          {text.slice(e.start, e.end)}
        </Mark>
      </Tooltip>,
    );
    cursor = e.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));

  return <Text style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{parts}</Text>;
}
