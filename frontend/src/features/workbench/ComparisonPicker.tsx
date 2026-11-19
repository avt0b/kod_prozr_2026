import { ActionIcon, Button, Group, Stack, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPlus, IconSearch, IconX } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useOfficials } from '@/features/officials/api';
import { QueryState, RiskScoreBadge } from '@/shared/ui';
import { useWorkbench } from './context';
import { COMPARISON_LIMIT } from './model';

export function ComparisonPicker({ onClose }: { onClose: () => void }) {
  const { state, toggleComparison } = useWorkbench();
  const [search, setSearch] = useState('');
  const [debounced] = useDebouncedValue(search, 250);
  const officials = useOfficials({
    query: debounced.trim() || undefined,
    sort: '-risk_score',
    limit: 10,
    offset: 0,
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const full = state.comparison.length >= COMPARISON_LIMIT;
  useEffect(() => inputRef.current?.focus(), []);
  const selected = new Set(state.comparison.map((item) => item.id));
  const searching = officials.isFetching || search.trim() !== debounced.trim();
  return (
    <section className="comparison-picker" aria-label="Выбор служащего для сравнения">
      <Group justify="space-between" mb="md">
        <div>
          <Text fw={600}>Добавить в сравнение</Text>
          <Text c="dimmed" size="sm">
            {full
              ? 'Все три места заняты. Уберите кейс, чтобы выбрать другой.'
              : 'Выберите из рейтинга или найдите служащего по имени.'}
          </Text>
        </div>
        <ActionIcon
          ref={closeRef}
          variant="subtle"
          color="gray"
          aria-label="Закрыть выбор служащего"
          onClick={onClose}
        >
          <IconX size={18} />
        </ActionIcon>
      </Group>
      {!full && (
        <>
          <TextInput
            ref={inputRef}
            label="Поиск служащего для сравнения"
            placeholder="ФИО или должность"
            leftSection={<IconSearch size={18} />}
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
          />
          {searching && (
            <Text role="status" size="xs" c="dimmed" mt="xs">
              Ищу служащих…
            </Text>
          )}
          <div className="comparison-picker-results">
            <QueryState
              query={officials}
              isEmpty={(data) => !searching && data.items.every((item) => selected.has(item.id))}
              empty="Доступных служащих по этому запросу нет. Измените запрос; выбранные кейсы не повторяются."
            >
              {(data) => (
                <Stack gap={0}>
                  {data.items
                    .filter((item) => !selected.has(item.id))
                    .map((item) => (
                      <div className="comparison-candidate" key={item.id}>
                        <div>
                          <Text fw={600} size="sm">
                            {item.full_name}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {item.position} · {item.organ}
                          </Text>
                        </div>
                        <Group gap="sm" wrap="nowrap">
                          <RiskScoreBadge score={item.risk_score} />
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<IconPlus size={14} />}
                            disabled={
                              officials.isPlaceholderData || search.trim() !== debounced.trim()
                            }
                            aria-label={`Добавить в сравнение: ${item.full_name}`}
                            onClick={() => {
                              toggleComparison({ id: item.id, name: item.full_name });
                              setSearch('');
                              requestAnimationFrame(() => {
                                if (state.comparison.length + 1 >= COMPARISON_LIMIT)
                                  closeRef.current?.focus();
                                else inputRef.current?.focus();
                              });
                            }}
                          >
                            Добавить
                          </Button>
                        </Group>
                      </div>
                    ))}
                </Stack>
              )}
            </QueryState>
          </div>
        </>
      )}
    </section>
  );
}
