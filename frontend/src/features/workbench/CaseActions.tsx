import { ActionIcon, Group, Tooltip } from '@mantine/core';
import { IconBookmark, IconBookmarkFilled, IconColumns3 } from '@tabler/icons-react';
import { useWorkbench } from './context';
import type { CaseRef } from './model';

export function CaseActions({ person }: { person: CaseRef }) {
  const { state, toggleSaved, toggleComparison } = useWorkbench();
  const saved = state.saved.some((item) => item.id === person.id);
  const compared = state.comparison.some((item) => item.id === person.id);
  return (
    <Group gap={4} wrap="nowrap" onClick={(event) => event.stopPropagation()}>
      <Tooltip label={saved ? 'Убрать из сохранённых' : 'Сохранить кейс'}>
        <ActionIcon
          className="case-action"
          variant={saved ? 'light' : 'subtle'}
          color={saved ? 'brand' : 'gray'}
          size="lg"
          aria-label={`${saved ? 'Убрать из сохранённых' : 'Сохранить кейс'}: ${person.name}`}
          aria-pressed={saved}
          onClick={() => toggleSaved(person)}
        >
          {saved ? <IconBookmarkFilled size={18} /> : <IconBookmark size={18} />}
        </ActionIcon>
      </Tooltip>
      <Tooltip label={compared ? 'Убрать из сравнения' : 'Добавить к сравнению'}>
        <ActionIcon
          className="case-action"
          variant={compared ? 'light' : 'subtle'}
          color={compared ? 'brand' : 'gray'}
          size="lg"
          aria-label={`${compared ? 'Убрать из сравнения' : 'Добавить к сравнению'}: ${person.name}`}
          aria-pressed={compared}
          onClick={() => toggleComparison(person)}
        >
          <IconColumns3 size={18} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );
}
