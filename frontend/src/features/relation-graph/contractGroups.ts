import type { OfficialGraph } from '@/shared/api';

/** Labels are rounded by the API, so their total is explicitly approximate. */
export function labelAmount(label: string): number | null {
  const match = label.match(/([\d\s\u00a0]+(?:[.,]\d+)?)\s*(млрд|млн|тыс\.?)?\s*(?:₽|руб\.)/);
  if (!match) return null;
  const value = Number(match[1].replace(/\s/g, '').replace(',', '.'));
  const scale = match[2]?.startsWith('млрд')
    ? 1e9
    : match[2]?.startsWith('млн')
      ? 1e6
      : match[2]?.startsWith('тыс')
        ? 1e3
        : 1;
  return Number.isFinite(value) ? value * scale : null;
}
export function groupContracts(graph: OfficialGraph, highlight: string[] = []) {
  const groups = new Map<string, string[]>();
  for (const node of graph.nodes.filter((n) => n.type === 'contract')) {
    const supplier = graph.edges.find((e) => e.target === node.id && e.type === 'supplier');
    const customer = graph.edges.find((e) => e.source === node.id && e.type === 'customer');
    if (!supplier || !customer) continue;
    const key = `${supplier.source}:${customer.target}`;
    groups.set(key, [...(groups.get(key) ?? []), node.id]);
  }
  const aliases = new Map<string, string>();
  const added: OfficialGraph['nodes'] = [];
  for (const [key, ids] of groups) {
    if (ids.length < 4) continue;
    const highlighted = ids.filter((id) => highlight.includes(id)).length;
    if (highlighted > 0 && highlighted < ids.length) continue;
    const amounts = ids.map((id) => labelAmount(graph.nodes.find((n) => n.id === id)!.label));
    if (amounts.some((v) => v === null)) continue;
    const id = `contracts:${key}`;
    ids.forEach((original) => aliases.set(original, id));
    const total = amounts.reduce<number>((sum, amount) => sum + amount!, 0);
    added.push({
      id,
      type: 'contract',
      label: `${ids.length} контрактов\n≈ ${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(total / 1e6)} млн ₽`,
    });
  }
  const seen = new Set<string>();
  const edges = graph.edges
    .map((edge) => ({
      ...edge,
      source: aliases.get(edge.source) ?? edge.source,
      target: aliases.get(edge.target) ?? edge.target,
    }))
    .filter((edge) => {
      const key = `${edge.source}:${edge.target}:${edge.type}${edge.manual ? `:${edge.id}` : ''}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  return {
    graph: { ...graph, nodes: [...graph.nodes.filter((n) => !aliases.has(n.id)), ...added], edges },
    aliases,
  };
}
