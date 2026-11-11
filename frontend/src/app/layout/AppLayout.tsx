import {
  ActionIcon,
  AppShell,
  Badge,
  Burger,
  Group,
  NavLink,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconChartBar,
  IconListNumbers,
  IconMessageChatbot,
  IconMoon,
  IconShieldSearch,
  IconSun,
  IconMail,
} from '@tabler/icons-react';
import { NavLink as RouterNavLink, Outlet, useLocation } from 'react-router';
import { env } from '@/shared/config/env';
import { routes } from '@/shared/config/routes';

const NAV = [
  { to: routes.overview(), label: 'Обзор', icon: IconChartBar, end: true },
  { to: routes.officials(), label: 'Рейтинг служащих', icon: IconListNumbers, end: false },
  { to: routes.appeals(), label: 'Обращения', icon: IconMail, end: false },
  { to: routes.assistant(), label: 'Ассистент', icon: IconMessageChatbot, end: false },
];

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme('light');
  return (
    <Tooltip label="Сменить тему">
      <ActionIcon
        variant="default"
        size="lg"
        aria-label="Сменить тему"
        onClick={() => setColorScheme(computed === 'light' ? 'dark' : 'light')}
      >
        {computed === 'light' ? <IconMoon size={18} /> : <IconSun size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconShieldSearch size={24} color="var(--mantine-primary-color-filled)" />
            <Text fw={600}>Рабочее место аналитика</Text>
            {env.useMocks && (
              <Tooltip label="Данные из src/shared/api/mocks (VITE_USE_MOCKS=true)">
                <Badge variant="light" color="orange">
                  моки
                </Badge>
              </Tooltip>
            )}
          </Group>
          <ColorSchemeToggle />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            component={RouterNavLink}
            to={item.to}
            end={item.end}
            label={item.label}
            leftSection={<item.icon size={18} />}
            active={item.end ? pathname === item.to : pathname.startsWith(item.to)}
            onClick={close}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
