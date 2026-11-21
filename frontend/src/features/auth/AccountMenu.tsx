import { useState, useSyncExternalStore } from 'react';
import { Button, Menu } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { IconLogout, IconUserCircle } from '@tabler/icons-react';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useReducedMotion } from '@mantine/hooks';
import { getSnapshot, logout, subscribe } from '@/shared/lib/authSession';

export function AccountMenu() {
  const { user } = useSyncExternalStore(subscribe, getSnapshot);
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const reducedMotion = useReducedMotion();
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
        <Menu.Label>{user?.username}</Menu.Label>
        <Menu.Item
          disabled={reducedMotion}
          leftSection={<IconPlayerPlay size={17} />}
          onClick={() => {
            const page = document.querySelector<HTMLElement>('.workspace-page');
            if (!page) return;
            page.setAttribute('data-motion-reset', '');
            void page.offsetWidth;
            page.removeAttribute('data-motion-reset');
            document.dispatchEvent(new Event('workspace:replay-motion'));
          }}
        >
          Повторить анимации
        </Menu.Item>
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
