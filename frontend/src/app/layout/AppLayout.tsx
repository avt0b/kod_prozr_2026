import {
  ActionIcon,
  AppShell,
  Badge,
  Burger,
  Group,
  NavLink,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import type { CSSProperties } from 'react';
import {
  IconChartBar,
  IconListNumbers,
  IconMap2,
  IconMessageChatbot,
  IconMoon,
  IconShieldSearch,
  IconSun,
  IconMail,
} from '@tabler/icons-react';
import { Link, NavLink as RouterNavLink, Outlet, useLocation } from 'react-router';
import { env } from '@/shared/config/env';
import { routes } from '@/shared/config/routes';
import { useLiquidGlass } from '@/shared/ui/useLiquidGlass';
import { useControlGlint } from './useControlGlint';

const NAV = [
  { to: routes.overview(), label: 'Обзор', icon: IconChartBar, end: true },
  { to: routes.officials(), label: 'Рейтинг служащих', icon: IconListNumbers, end: false },
  { to: routes.riskMap(), label: 'Карта рисков', icon: IconMap2, end: false },
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
  const headerGlass = useLiquidGlass<HTMLElement>();
  const navigationGlass = useLiquidGlass<HTMLElement>();
  const activeSection = NAV.findIndex((item) =>
    item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`),
  );
  useControlGlint();

  return (
    <AppShell
      className="workspace-shell"
      header={{ height: 76 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header className="workspace-header workspace-glass" {...headerGlass.props}>
        {headerGlass.lens}
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs" wrap="nowrap">
            <Burger
              opened={opened}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
              aria-label="Меню разделов"
              aria-expanded={opened}
              aria-controls="workspace-navigation"
            />
            <Link className="workspace-brand" to={routes.overview()} onClick={close}>
              <IconShieldSearch size={24} color="var(--mantine-primary-color-filled)" />
              <span className="workspace-brand-title">Рабочее место аналитика</span>
            </Link>
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

      <AppShell.Navbar
        id="workspace-navigation"
        aria-label="Разделы приложения"
        data-menu-open={opened || undefined}
        className="workspace-navbar workspace-glass"
        p="sm"
        {...navigationGlass.props}
      >
        {navigationGlass.lens}
        <div
          className="workspace-nav-list"
          style={{ '--workspace-active-section': Math.max(0, activeSection) } as CSSProperties}
        >
          <span
            className="workspace-nav-selection"
            data-visible={activeSection >= 0 || undefined}
            aria-hidden="true"
          />
          {NAV.map((item, index) => (
            <NavLink
              key={item.to}
              className="workspace-nav-item"
              component={RouterNavLink}
              to={item.to}
              end={item.end}
              label={item.label}
              leftSection={<item.icon size={18} />}
              active={activeSection === index}
              onClick={close}
            />
          ))}
        </div>
      </AppShell.Navbar>

      <AppShell.Main className="workspace-main">
        <div className="workspace-page" key={pathname}>
          <Outlet />
        </div>
      </AppShell.Main>
    </AppShell>
  );
}
