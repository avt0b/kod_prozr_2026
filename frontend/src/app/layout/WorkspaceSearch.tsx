import { Button, Group, Modal, TextInput } from '@mantine/core';
import { useDisclosure, useHotkeys } from '@mantine/hooks';
import { IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { routes } from '@/shared/config/routes';

export function WorkspaceSearch() {
  const [opened, { open, close }] = useDisclosure();
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  useHotkeys([['mod+K', open]]);
  return (
    <>
      <button
        type="button"
        className="workspace-search-trigger"
        onClick={open}
        aria-label="Найти служащего"
      >
        <IconSearch size={17} />
        <span>Найти служащего</span>
        <kbd>Ctrl K</kbd>
      </button>
      <Modal opened={opened} onClose={close} title="Поиск служащего" centered>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!query.trim()) return;
            navigate(`${routes.officials()}?${new URLSearchParams({ query: query.trim() })}`);
            close();
          }}
        >
          <TextInput
            data-autofocus
            label="ФИО служащего"
            placeholder="Например, Соколов"
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            leftSection={<IconSearch size={18} />}
            size="md"
          />
          <Group justify="flex-end" mt="lg">
            <Button type="submit" disabled={!query.trim()}>
              Найти в рейтинге
            </Button>
          </Group>
        </form>
      </Modal>
    </>
  );
}
