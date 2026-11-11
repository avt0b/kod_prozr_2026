import { Group, Select } from '@mantine/core';
import type { AppealCategory, AppealStatus } from '@/shared/api';
import { APPEAL_CATEGORY_LABELS, APPEAL_STATUS_LABELS } from '@/shared/lib/labels';

export interface AppealFilterValues {
  status: AppealStatus | null;
  category: AppealCategory | null;
}

const toOptions = (dict: Record<string, string>) =>
  Object.entries(dict).map(([value, label]) => ({ value, label }));

export function AppealFilters({
  value,
  onChange,
}: {
  value: AppealFilterValues;
  onChange: (v: AppealFilterValues) => void;
}) {
  return (
    <Group gap="md" align="flex-end">
      <Select
        label="Статус"
        placeholder="Все"
        clearable
        data={toOptions(APPEAL_STATUS_LABELS)}
        value={value.status}
        onChange={(s) => onChange({ ...value, status: s as AppealStatus | null })}
        w={200}
      />
      <Select
        label="Категория"
        placeholder="Все"
        clearable
        data={toOptions(APPEAL_CATEGORY_LABELS)}
        value={value.category}
        onChange={(c) => onChange({ ...value, category: c as AppealCategory | null })}
        w={240}
      />
    </Group>
  );
}
