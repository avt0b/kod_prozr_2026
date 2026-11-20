import {
  ActionIcon,
  AppShell,
  Badge,
  Box,
  Group,
  NavLink,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import {
  IconChartBar,
  IconChevronDown,
  IconListNumbers,
  IconMail,
  IconMap2,
  IconMessageChatbot,
  IconMoon,
  IconShieldSearch,
  IconSun,
} from '@tabler/icons-react';
import { useEffect, useId, useLayoutEffect, useState, type CSSProperties } from 'react';
import { Link, NavLink as RouterNavLink, Outlet, useLocation, useMatch } from 'react-router';
import { WorkbenchPanels } from '@/features/workbench/WorkbenchPanels';
import { WorkbenchTools } from '@/features/workbench/WorkbenchTools';
import { env } from '@/shared/config/env';
import { routes } from '@/shared/config/routes';
import { useLiquidGlass } from '@/shared/ui/useLiquidGlass';
import { useControlGlint } from './useControlGlint';
import { MotionReplay } from './MotionReplay';
import { WorkspaceSearch } from './WorkspaceSearch';

const PROFILE_NAV_CAPTIONS = [
  'Сводная аналитика региона',
  'Граф связей служащего',
  'Должности и ведомства',
  'Сигналы граждан',
  'Вопросы к данным',
];

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

function ProfileNavigation() {
  const id = useId();
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 65em)').matches);
  return (
    <div className="profile-navigation" data-open={open || undefined}>
      <button
        className="profile-navigation-toggle profile-glass"
        type="button"
        aria-label="Код прозрачности"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="workspace-brand-mark">
          <IconShieldSearch size={21} aria-hidden />
        </span>
        <span className="profile-brand-label">
          <strong>Код прозрачности</strong>
          <small>Кабинет аналитика</small>
        </span>
        <IconChevronDown className="profile-navigation-chevron" size={16} aria-hidden />
      </button>
      <div className="profile-navigation-reveal" aria-hidden={!open}>
        <div className="profile-navigation-clip">
          <nav id={id} className="profile-glass" aria-label="Разделы приложения">
            {NAV.map((item, index) => (
              <RouterNavLink
                key={item.to}
                to={item.to}
                end={item.end}
                tabIndex={open ? undefined : -1}
              >
                <span className="profile-nav-glyph" data-section={index}>
                  <item.icon size={16} aria-hidden />
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>{PROFILE_NAV_CAPTIONS[index]}</small>
                </span>
              </RouterNavLink>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}

export function AppLayout() {
  const [presentation, setPresentation] = useState(false);
  useEffect(() => {
    if (!presentation) return;
    const exit = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !document.querySelector('[role="dialog"]'))
        setPresentation(false);
    };
    // Capture Escape before a focused tooltip consumes it; open dialogs retain priority.
    window.addEventListener('keydown', exit, true);
    return () => window.removeEventListener('keydown', exit, true);
  }, [presentation]);
  const { pathname } = useLocation();
  const profileCanvas = useMatch(routes.official(':id'));
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
  useEffect(() => {
    const syncVisibility = () =>
      document.documentElement.toggleAttribute('data-motion-paused', document.hidden);
    syncVisibility();
    document.addEventListener('visibilitychange', syncVisibility);
    return () => {
      document.removeEventListener('visibilitychange', syncVisibility);
      document.documentElement.removeAttribute('data-motion-paused');
    };
  }, []);
  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname]);

  const tools = (
    <Group gap="xs" wrap="nowrap">
      <WorkspaceSearch />
      <WorkbenchTools
        presentation={presentation}
        onPresentation={() => setPresentation((value) => !value)}
      />
      <MotionReplay />
      <Box visibleFrom="sm">
        <ColorSchemeToggle />
      </Box>
    </Group>
  );
  if (profileCanvas) {
    return (
      <div
        className="workspace-shell profile-canvas-shell"
        data-presentation={presentation || undefined}
      >
        <a className="workspace-skip-link" href="#workspace-content">
          К содержимому
        </a>
        <header className="profile-canvas-header">
          <ProfileNavigation key={pathname} />
          {tools}
        </header>
        <main
          className="workspace-page profile-canvas-page"
          key={pathname}
          id="workspace-content"
          tabIndex={-1}
        >
          <Outlet />
        </main>
        <WorkbenchPanels />
      </div>
    );
  }

  return (
    <AppShell
      className="workspace-shell"
      data-presentation={presentation || undefined}
      header={{ height: { base: 82, sm: 94 } }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: true, desktop: presentation } }}
      padding={{ base: 14, sm: 24 }}
    >
      <a className="workspace-skip-link" href="#workspace-content">
        К содержимому
      </a>
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
          {tools}
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

      <AppShell.Main className="workspace-main" id="workspace-content" tabIndex={-1}>
        <div className="workspace-page" key={pathname}>
          <Outlet />
        </div>
      </AppShell.Main>
      {!presentation && <MobileNavigation />}
      <WorkbenchPanels />
    </AppShell>
  );
}
