import {
  ActionIcon,
  AppShell,
  Badge,
  Group,
  NavLink,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import {
  IconChartBar,
  IconListNumbers,
  IconMail,
  IconMap2,
  IconMessageChatbot,
  IconMoon,
  IconShieldSearch,
  IconSun,
} from '@tabler/icons-react';
import type { CSSProperties } from 'react';
import { Link, NavLink as RouterNavLink, Outlet, useLocation } from 'react-router';
import { env } from '@/shared/config/env';
import { routes } from '@/shared/config/routes';
import { useLiquidGlass } from '@/shared/ui/useLiquidGlass';
import { useControlGlint } from './useControlGlint';

const NAV = [
  { to: routes.overview(), label: 'Обзор', compact: 'Обзор', icon: IconChartBar, end: true },
  {
    to: routes.officials(),
    label: 'Рейтинг служащих',
    compact: 'Рейтинг',
    icon: IconListNumbers,
    end: false,
  },
  { to: routes.riskMap(), label: 'Карта рисков', compact: 'Риски', icon: IconMap2, end: true },
  { to: routes.appeals(), label: 'Обращения', compact: 'Обращения', icon: IconMail, end: false },
  {
    to: routes.assistant(),
    label: 'Ассистент',
    compact: 'Ассистент',
    icon: IconMessageChatbot,
    end: true,
  },
];

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme('light');
  return (
    <Tooltip label="Сменить тему">
      <ActionIcon
        variant="default"
        size={40}
        aria-label="Сменить тему"
        onClick={() => setColorScheme(computed === 'light' ? 'dark' : 'light')}
      >
        {computed === 'light' ? <IconMoon size={18} /> : <IconSun size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

function MobileNavigation() {
  return (
    <nav className="workspace-mobile-nav workspace-glass" aria-label="Разделы приложения">
      {NAV.map((item) => (
        <RouterNavLink to={item.to} end={item.end} key={item.to} aria-label={item.label}>
          <item.icon size={19} aria-hidden />
          <span>{item.compact}</span>
        </RouterNavLink>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const headerGlass = useLiquidGlass<HTMLElement>();
  const navigationGlass = useLiquidGlass<HTMLElement>();
  const activeSection = NAV.findIndex((item) =>
    item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`),
  );
  const section = NAV[activeSection];
  const SectionIcon = section?.icon ?? IconShieldSearch;
  const sectionLabel =
    section?.label ?? (pathname.startsWith(routes.report('')) ? 'Докладная' : 'Код прозрачности');
  useControlGlint();

  return (
    <AppShell
      className="workspace-shell"
      header={{ height: { base: 82, sm: 94 } }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: true } }}
      padding={{ base: 14, sm: 24 }}
    >
      <AppShell.Header className="workspace-header workspace-glass" {...headerGlass.props}>
        {headerGlass.lens}
        <Group justify="space-between" h="100%" px="sm" wrap="nowrap" gap="xs">
          <Group wrap="nowrap" gap="xs" className="workspace-section">
            <SectionIcon size={18} aria-hidden />
            <span className="workspace-section-label">{sectionLabel}</span>
            {env.useMocks && (
              <Badge hiddenFrom="sm" variant="light" color="orange">
                моки
              </Badge>
            )}
          </Group>
          <ColorSchemeToggle />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar
        aria-label="Разделы приложения"
        className="workspace-navbar workspace-glass"
        visibleFrom="sm"
        p={10}
        {...navigationGlass.props}
      >
        {navigationGlass.lens}
        <Link className="workspace-brand" to={routes.overview()}>
          <span className="workspace-brand-mark">
            <IconShieldSearch size={21} aria-hidden />
          </span>
          <span>
            <span className="workspace-brand-title">Код прозрачности</span>
            <span className="workspace-brand-caption">Кабинет аналитика</span>
          </span>
        </Link>
        <div
          className="workspace-nav-list"
          style={{ '--workspace-active-section': Math.max(0, activeSection) } as CSSProperties}
        >
          <span
            className="workspace-nav-selection"
            data-visible={activeSection >= 0 || undefined}
            aria-hidden
          />
          {NAV.map((item, index) => (
            <NavLink
              key={item.to}
              className="workspace-nav-item"
              component={RouterNavLink}
              to={item.to}
              end={item.end}
              label={item.label}
              leftSection={<item.icon size={19} />}
              active={activeSection === index}
            />
          ))}
        </div>
        {env.useMocks && (
          <div className="workspace-data-mode" aria-label="Демонстрационные данные">
            <span aria-hidden />
            моки
          </div>
        )}
      </AppShell.Navbar>

      <AppShell.Main className="workspace-main">
        <div className="workspace-page">
          <Outlet />
        </div>
      </AppShell.Main>
      <MobileNavigation />
    </AppShell>
  );
}
