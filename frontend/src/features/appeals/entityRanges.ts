import type { AppealEntity } from '@/shared/api';

/** Python counts Unicode code points, JavaScript counts UTF-16 code units. */
export function entityRanges(text: string, entities: AppealEntity[]): AppealEntity[] {
  const points = Array.from(text);
  const offsets = [0];
  for (const point of points) offsets.push(offsets[offsets.length - 1] + point.length);
  const valid = entities.flatMap((entity) => {
    const { start, end } = entity;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start) return [];
    if (end <= text.length && text.slice(start, end) === entity.text) return [entity];
    if (end <= points.length && points.slice(start, end).join('') === entity.text)
      return [{ ...entity, start: offsets[start], end: offsets[end] }];
    // Never highlight unrelated text when a model returns invalid offsets.
    return [];
  });
  valid.sort((a, b) => a.start - b.start || b.end - a.end);
  let cursor = 0;
  return valid.filter((entity) => {
    if (entity.start < cursor) return false;
    cursor = entity.end;
    return true;
  });
}
