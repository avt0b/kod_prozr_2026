import { Anchor, Group, Skeleton, Text } from '@mantine/core';
import { IconBuilding, IconUser } from '@tabler/icons-react';
import { Link } from 'react-router';
import { useOfficial, useOfficialGraph } from '@/features/officials/api';
import type { OfficialGraph, OfficialListItem } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { riskLevel } from '@/shared/lib/format';
import { AnimatedNumber } from '@/shared/ui/AnimatedNumber';
import type { CSSProperties } from 'react';

/** A compact view of actual graph edges, never an invented relationship illustration. */
function NetworkPreview({ graph, personId }: { graph: OfficialGraph; personId: string }) {
  const center = graph.nodes.find((node) => node.id === personId);
  if (!center) return null;
  const connected = new Set(
    graph.edges
      .filter((edge) => edge.source === personId || edge.target === personId)
      .flatMap((edge) => [edge.source, edge.target]),
  );
  const nodes = [
    center,
    ...graph.nodes
      .filter((node) => node.id !== personId)
      .sort((a, b) => Number(connected.has(b.id)) - Number(connected.has(a.id)))
      .slice(0, 10),
  ];
  const positions = new Map(
    nodes.map((node, index) => {
      const angle = ((index - 1) / Math.max(1, nodes.length - 1)) * Math.PI * 2 - Math.PI / 2;
      return [
        node.id,
        {
          x: index === 0 ? 240 : 240 + Math.cos(angle) * 174,
          y: index === 0 ? 154 : 154 + Math.sin(angle) * 112,
        },
      ];
    }),
  );
  return (
    <svg
      className="focus-network"
      viewBox="0 0 480 310"
      role="img"
      aria-label={`Фрагмент графа связей: ${nodes.length} узлов. Полный граф в профиле служащего.`}
    >
      <defs>
        <radialGradient id="network-glow">
          <stop stopColor="#407df0" stopOpacity=".22" />
          <stop offset="1" stopColor="#407df0" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="240" cy="154" r="150" fill="url(#network-glow)" />
      <ellipse cx="240" cy="154" rx="174" ry="112" className="network-orbit" />
      <circle cx="240" cy="154" r="75" className="network-scan" />
      {graph.edges
        .filter((edge) => positions.has(edge.source) && positions.has(edge.target))
        .map((edge, index) => {
          const source = positions.get(edge.source)!;
          const target = positions.get(edge.target)!;
          return (
            <g key={index} style={{ '--motion-index': index } as CSSProperties}>
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                className="network-edge"
                pathLength={1}
              />
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                pathLength={1}
                className="network-flow"
                aria-hidden="true"
              />
            </g>
          );
        })}
      {nodes.map((node, index) => {
        const position = positions.get(node.id)!;
        return (
          <g key={node.id} transform={`translate(${position.x} ${position.y})`}>
            <g className="network-node-stage" style={{ '--motion-index': index } as CSSProperties}>
              <title>{node.label}</title>
              <circle
                r={index === 0 ? 25 : 8}
                className={
                  index === 0 ? 'network-center' : `network-node network-node-${node.type}`
                }
              />
              {index === 0 && (
                <path
                  d="M-6-7a6 6 0 1 0 12 0a6 6 0 1 0-12 0M-11 12c0-12 22-12 22 0"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.8"
                />
              )}
              <text y={index === 0 ? 49 : 25} textAnchor="middle">
                {index === 0
                  ? 'Служащий'
                  : node.label.length > 22
                    ? `${node.label.slice(0, 21)}…`
                    : node.label}
              </text>
            </g>
          </g>
        );
      })}
    </svg>
  );
}

export function FocusCase({ official }: { official: OfficialListItem }) {
  const profile = useOfficial(official.id);
  const graph = useOfficialGraph(official.id);
  const flag = profile.data?.risk.flags.slice().sort((a, b) => b.weight - a.weight)[0];
  return (
    <article className="focus-case">
      <div className="focus-case-top">
        <span className="editorial-eyebrow">В фокусе проверки</span>
        <span className="focus-case-score" data-risk-level={riskLevel(official.risk_score)}>
          <AnimatedNumber value={official.risk_score} />
          <small> / 100</small>
        </span>
      </div>
      <div className="focus-visual">
        {graph.data ? (
          <NetworkPreview graph={graph.data} personId={official.id} />
        ) : graph.isError ? (
          <div className="focus-network-fallback">
            <IconBuilding size={40} />
            <Text>Не удалось загрузить граф. Повторите попытку в профиле служащего.</Text>
          </div>
        ) : (
          <Skeleton height={270} radius="lg" />
        )}
      </div>
      <div className="focus-case-person">
        <span className="focus-person-icon">
          <IconUser size={21} />
        </span>
        <div>
          <h2>{official.full_name}</h2>
          <p>{official.position}</p>
        </div>
      </div>
      <Text size="sm" c="dimmed" mt="sm">
        {official.organ}
      </Text>
      {flag && (
        <p className="focus-explanation">
          <span>{flag.rule_code}</span>
          {flag.explanation}
        </p>
      )}
      <Group justify="space-between" mt="lg">
        <Text size="xs" c="dimmed">
          Первый в рейтинге риска
        </Text>
        <Anchor component={Link} to={routes.official(official.id)} fw={600} size="sm">
          Открыть профиль
        </Anchor>
      </Group>
    </article>
  );
}
