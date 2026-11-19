import { Badge, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconScale } from '@tabler/icons-react';
import { useId, useState, type CSSProperties } from 'react';
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
  const explanationId = useId();
  const [showFullText, setShowFullText] = useState(false);
  const longExplanation = flag.explanation.length > 160;

  return (
    <div className="flag-evidence">
      <dl className="flag-evidence-details">
        <div>
          <dt>Факт и пояснение</dt>
          <dd>
            <Text
              id={explanationId}
              size="sm"
              lineClamp={longExplanation && !showFullText ? 3 : undefined}
            >
              {flag.explanation}
            </Text>
            {longExplanation && (
              <UnstyledButton
                type="button"
                className="flag-evidence-action"
                aria-controls={explanationId}
                aria-expanded={showFullText}
                onClick={() => setShowFullText((value) => !value)}
              >
                {showFullText ? 'Свернуть пояснение' : 'Читать полностью'}
              </UnstyledButton>
            )}
          </dd>
        </div>
        <div className="flag-legal">
          <dt>
            <IconScale size={15} aria-hidden />
            Правовое основание
          </dt>
          <dd>{flag.legal_ref || 'В данных не указано'}</dd>
        </div>
      </dl>
      <details className="flag-sources">
        <summary className="flag-evidence-action">
          <IconChevronDown size={14} aria-hidden />
          <span>Записи-источники</span>
          <span className="flag-source-count">{flag.evidence.length}</span>
        </summary>
        {flag.evidence.length ? (
          <ol>
            {flag.evidence.map((entry, index) => (
              <li key={`${entry.node_id}:${index}`}>
                <span className="flag-source-type">{NODE_TYPE_LABELS[entry.type]}</span>
                <span>{entry.label}</span>
              </li>
            ))}
          </ol>
        ) : (
          <Text size="xs" c="dimmed">
            В данных не указаны
          </Text>
        )}
      </details>
    </div>
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
    <Stack gap={4}>
      {flags.map((flag, index) => {
        const selected = flag.id === selectedId;
        const expanded = !expandedId || flag.id === expandedId;
        const evidenceId = `flag-details-${flag.id}`;
        const label = (
          <Group gap={8} wrap="nowrap" justify="space-between">
            <Badge
              className="flag-rule-code"
              color={SEVERITY_COLORS[flag.severity]}
              variant="light"
            >
              {flag.rule_code}
            </Badge>
            <Text size="sm" fw={650} style={{ flex: 1 }}>
              {RULE_TITLES[flag.rule_code]}
            </Text>
            <Text size="xs" c="dimmed" className="flag-weight">
              вес {flag.weight}
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
          <div
            key={flag.id}
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
            <div id={evidenceId} className="flag-details" hidden={!expanded}>
              {expanded && (
                <>
                  <Text size="xs" c="dimmed" mt="xs" mb={5}>
                    Риск {SEVERITY_LABELS[flag.severity]}
                  </Text>
                  <FlagEvidence flag={flag} />
                </>
              )}
            </div>
          </div>
        );
      })}
    </Stack>
  );
}
