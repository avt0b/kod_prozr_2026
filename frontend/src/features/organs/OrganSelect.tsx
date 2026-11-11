import { Select, type SelectProps } from '@mantine/core';
import { useOrgans } from './api';

type Props = Omit<SelectProps, 'data'>;

export function OrganSelect(props: Props) {
  const { data, isPending } = useOrgans();
  return (
    <Select
      label="Орган"
      placeholder={isPending ? 'Загрузка…' : 'Все органы'}
      clearable
      searchable
      data={(data?.items ?? []).map((o) => ({ value: o.id, label: o.name }))}
      {...props}
    />
  );
}
