import { useState, useSyncExternalStore } from 'react';
import { Button, Menu } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { IconLogout, IconUserCircle } from '@tabler/icons-react';
import { getSnapshot, logout, ROLE_LABELS, subscribe } from '@/shared/lib/authSession';

export function AccountMenu() {
  const { user } = useSyncExternalStore(subscribe, getSnapshot);
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  async function leave() {
    setBusy(true);
    try {
      await logout();
      await client.cancelQueries();
      client.clear();
    } catch {
      notifications.show({
        color: 'red',
        message: 'Не удалось завершить сессию. Повторите выход.',
      });
    } finally {
      setBusy(false);
    }
  }
  return (
    <Menu
      position="bottom-end"
      floatingStrategy="fixed"
      transitionProps={{ transition: 'fade', duration: 120 }}
    >
      <Menu.Target>
        <Button
          className="account-menu-trigger"
          variant="subtle"
          size="compact-md"
          aria-label="Учётная запись"
          leftSection={<IconUserCircle size={20} />}
        >
          {user?.username}
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>
          {user?.username}
          {user && ` · ${ROLE_LABELS[user.role]}`}
        </Menu.Label>
        <Menu.Item
          disabled={busy}
          leftSection={<IconLogout size={17} />}
          onClick={() => void leave()}
        >
          Выйти
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
