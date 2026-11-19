import { Badge, Card, Group, Stack, Text, ThemeIcon, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconChevronRight, IconScale } from '@tabler/icons-react';
import { Fragment, type CSSProperties } from 'react';
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
    <>
      <Text size="sm">{flag.explanation}</Text>
      {flag.legal_ref && (
        <Group gap={6} mt="xs" wrap="nowrap" align="flex-start">
          <ThemeIcon size="sm" variant="light" color="brand">
            <IconScale size={14} aria-hidden />
          </ThemeIcon>
          <Text size="xs" c="dimmed">
            {flag.legal_ref}
          </Text>
        </Group>
      )}
      {flag.evidence.length > 0 && (
        <Group gap={4} mt="xs" aria-label="Узлы цепочки">
          <Text size="xs" c="dimmed">
            Цепочка:
          </Text>
          {flag.evidence.map((node, index) => (
            <Fragment key={`${node.node_id}:${index}`}>
              {index > 0 && <IconChevronRight size={12} aria-hidden />}
              <Badge
                size="sm"
                variant="outline"
                color="gray"
                tt="none"
                radius="sm"
                fw={500}
                h="auto"
                py={2}
                maw="100%"
                title={`${NODE_TYPE_LABELS[node.type]}: ${node.label}`}
                styles={{ label: { whiteSpace: 'normal', overflow: 'visible', textAlign: 'left' } }}
              >
                {node.label}
              </Badge>
            </Fragment>
          ))}
        </Group>
      )}
    </>
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
