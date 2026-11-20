import type { GraphNodeType } from '@/shared/api';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';
import { GRAPH_APPEARANCE } from './graphAppearance';

export function GraphEntityIcon({ type, size = 18 }: { type: GraphNodeType; size?: number }) {
  return (
    <span className="graph-entity-icon" data-type={type} aria-hidden="true">
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <path
          d={GRAPH_APPEARANCE[type].path}
          stroke="currentColor"
          strokeWidth={1.65}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

export function GraphLegend() {
  return (
    <ul className="profile-graph-legend" aria-label="Типы узлов">
      {(Object.keys(GRAPH_APPEARANCE) as GraphNodeType[]).map((type) => (
        <li key={type}>
          <GraphEntityIcon type={type} size={14} />
          {NODE_TYPE_LABELS[type]}
        </li>
      ))}
    </ul>
  );
}
