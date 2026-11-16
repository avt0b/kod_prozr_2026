import { Group, NumberInput, Select, TextInput } from '@mantine/core';
import { useDebouncedCallback } from '@mantine/hooks';
import { IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { OrganSelect } from '@/features/organs/OrganSelect';
import type { RuleCode } from '@/shared/api';
import { RULE_TITLES } from '@/shared/lib/labels';

const RULE_OPTIONS = (Object.keys(RULE_TITLES) as RuleCode[]).map((code) => ({
  value: code,
  label: `${code} — ${RULE_TITLES[code]}`,
}));

export interface OfficialsFilterValues {
  query: string;
  organId: string | null;
  minScore: number | null;
  ruleCode: RuleCode | null;
}

interface Props {
  value: OfficialsFilterValues;
  onChange: (value: OfficialsFilterValues) => void;
}

export function OfficialsFilters({ value, onChange }: Props) {
  // Поиск печатаем локально и отправляем с задержкой, чтобы не дёргать API на каждую букву
  const [query, setQuery] = useState(value.query);
  const pushQuery = useDebouncedCallback((q: string) => onChange({ ...value, query: q }), 300);

  return (
    <Group align="flex-end" gap="md" wrap="wrap">
      <TextInput
        label="Поиск"
        placeholder="ФИО или должность"
        leftSection={<IconSearch size={16} />}
        value={query}
        onChange={(e) => {
          setQuery(e.currentTarget.value);
          pushQuery(e.currentTarget.value);
        }}
        w={280}
      />
      <OrganSelect
        value={value.organId}
        onChange={(organId) => onChange({ ...value, organId })}
        w={360}
      />
      <NumberInput
        label="Мин. балл"
        placeholder="0"
        min={0}
        max={100}
        step={10}
        value={value.minScore ?? ''}
        onChange={(v) => onChange({ ...value, minScore: v === '' ? null : Number(v) })}
        w={120}
      />
      <Select
        label="Правило"
        placeholder="Любое"
        data={RULE_OPTIONS}
        value={value.ruleCode}
        onChange={(v) => onChange({ ...value, ruleCode: (v as RuleCode | null) ?? null })}
        clearable
        w={340}
      />
    </Group>
  );
}
