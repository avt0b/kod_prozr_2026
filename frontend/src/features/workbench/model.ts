export interface CaseRef {
  id: string;
  name: string;
}
export interface WorkbenchState {
  version: 1;
  saved: CaseRef[];
  comparison: CaseRef[];
}
export const COMPARISON_LIMIT = 3;
export const SAVED_LIMIT = 50;
export const EMPTY_WORKBENCH: WorkbenchState = { version: 1, saved: [], comparison: [] };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function references(input: unknown, limit: number): CaseRef[] {
  if (!Array.isArray(input)) return [];
  const seen = new Set<string>();
  const result: CaseRef[] = [];
  for (const value of input) {
    if (
      !value ||
      typeof value !== 'object' ||
      typeof value.id !== 'string' ||
      !UUID.test(value.id) ||
      typeof value.name !== 'string' ||
      !value.name.trim()
    )
      continue;
    const id = value.id.toLowerCase();
    if (seen.has(id)) continue;
    seen.add(id);
    result.push({ id, name: value.name.trim().slice(0, 160) });
    if (result.length === limit) break;
  }
  return result;
}

export function decodeWorkbench(raw: string | undefined | null): WorkbenchState {
  try {
    const value: unknown = JSON.parse(raw ?? 'null');
    if (!value || typeof value !== 'object' || !('version' in value) || value.version !== 1)
      return EMPTY_WORKBENCH;
    return {
      version: 1,
      saved: references('saved' in value ? value.saved : [], SAVED_LIMIT),
      comparison: references('comparison' in value ? value.comparison : [], COMPARISON_LIMIT),
    };
  } catch {
    return EMPTY_WORKBENCH;
  }
}

export function toggleCase(items: CaseRef[], item: CaseRef, limit: number): CaseRef[] {
  const valid = references([item], 1)[0];
  if (!valid) return items;
  if (items.some((current) => current.id === valid.id))
    return items.filter((current) => current.id !== valid.id);
  if (items.length >= limit) return items;
  return [...items, valid];
}
