import { Badge, Card, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown } from '@tabler/icons-react';
import type { CSSProperties } from 'react';
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
  expandedId?: string;
  onSelect?: (flag: RiskFlag | null) => void;
}

function FlagEvidence({ flag }: { flag: RiskFlag }) {
  return (
    <dl className="flag-evidence-details">
      <div>
        <dt>Факт и пояснение</dt>
        <dd>{flag.explanation}</dd>
      </div>
      <div>
        <dt>Записи-источники</dt>
        <dd>
          {flag.evidence.length ? (
            <ol>
              {flag.evidence.map((e, index) => (
                <li key={`${e.node_id}:${index}`}>
                  <span className="flag-source-type">{NODE_TYPE_LABELS[e.type]}</span>
                  <span title={e.node_id}>{e.label}</span>
                </li>
              ))}
            </ol>
          ) : (
            <Text size="sm" c="dimmed">
              В данных не указаны
            </Text>
          )}
        </dd>
      </div>
      <div>
        <dt>Правовое основание</dt>
        <dd>
          {flag.legal_ref || (
            <Text size="sm" c="dimmed">
              В данных не указано
            </Text>
          )}
        </dd>
      </div>
    </dl>
  );
}

export function FlagList({ flags, selectedId, expandedId, onSelect }: Props) {
  if (!flags.length) {
    return (
      <Text c="dimmed" size="sm">
        Флагов риска не выявлено.
      </Text>
    );
  }

  return (
    <Stack gap={8}>
      {flags.map((flag, index) => {
        const selected = flag.id === selectedId;
        const expanded = !expandedId || flag.id === expandedId;
        const evidenceId = `flag-details-${flag.id}`;
        const label = (
          <Group gap={8} wrap="nowrap" justify="space-between">
            <Badge color={SEVERITY_COLORS[flag.severity]} variant="light" style={{ flexShrink: 0 }}>
              {flag.rule_code}
            </Badge>
            <Text size="sm" fw={650} style={{ flex: 1 }}>
              {RULE_TITLES[flag.rule_code]}
            </Text>
            {onSelect && (
              <IconChevronDown
                size={15}
                aria-hidden
                style={{ flexShrink: 0, rotate: expanded ? '180deg' : undefined }}
              />
            )}
          </Group>
        );
        return (
          <Card
            key={flag.id}
            padding="xs"
            className="workspace-flag"
            style={{ '--motion-index': Math.min(index, 5) } as CSSProperties}
            data-selectable={onSelect ? '' : undefined}
            data-severity={flag.severity}
            data-expanded={expanded || undefined}
            data-selected={selected || undefined}
          >
            {onSelect ? (
              <UnstyledButton
                className="workspace-flag-trigger"
                type="button"
                aria-pressed={selected}
                aria-expanded={expanded}
                aria-controls={evidenceId}
                onClick={() => onSelect(selected ? null : flag)}
              >
                {label}
              </UnstyledButton>
            ) : (
              label
            )}
            <div id={evidenceId} hidden={!expanded}>
              {expanded && (
                <>
                  <Text size="xs" c="dimmed" mt="xs" mb={5}>
                    Риск {SEVERITY_LABELS[flag.severity]} · вес {flag.weight}
                  </Text>
                  <FlagEvidence flag={flag} />
                </>
              )}
            </div>
          </Card>
        );
      })}
    </Stack>
  );
}
