import {
  ActionIcon,
  Box,
  Group,
  Indicator,
  Menu,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import {
  IconBookmark,
  IconColumns3,
  IconDots,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconMoon,
} from '@tabler/icons-react';
import { useWorkbench } from './context';

export function WorkbenchTools({
  presentation,
  onPresentation,
}: {
  presentation: boolean;
  onPresentation: () => void;
}) {
  const { state, openPanel } = useWorkbench();
  const { setColorScheme } = useMantineColorScheme();
  const scheme = useComputedColorScheme('light');
  const FocusIcon = presentation ? IconLayoutSidebarLeftExpand : IconLayoutSidebarLeftCollapse;
  return (
    <>
      <Group gap="xs" visibleFrom="sm" className="workbench-toolbar">
        <Tooltip label={`Сохранённые кейсы (${state.saved.length})`}>
          <Indicator disabled={!state.saved.length} label={state.saved.length} size={16}>
            <ActionIcon
              variant="default"
              size="lg"
              aria-label="Открыть сохранённые кейсы"
              onClick={() => openPanel('saved')}
            >
              <IconBookmark size={18} />
            </ActionIcon>
          </Indicator>
        </Tooltip>
        <Tooltip label={`Сравнение (${state.comparison.length}/3)`}>
          <Indicator disabled={!state.comparison.length} label={state.comparison.length} size={16}>
            <ActionIcon
              variant="default"
              size="lg"
              aria-label="Открыть сравнение"
              onClick={() => openPanel('comparison')}
            >
              <IconColumns3 size={18} />
            </ActionIcon>
          </Indicator>
        </Tooltip>
        <Tooltip
          label={
            presentation ? 'Выйти из режима презентации' : 'Режим презентации · Escape — выход'
          }
        >
          <ActionIcon
            variant={presentation ? 'light' : 'default'}
            size="lg"
            aria-label={presentation ? 'Выйти из режима презентации' : 'Режим презентации'}
            aria-pressed={presentation}
            onClick={onPresentation}
          >
            <FocusIcon size={19} />
          </ActionIcon>
        </Tooltip>
      </Group>
      <Box hiddenFrom="sm">
        <Menu position="bottom-end" shadow="md" width={260}>
          <Menu.Target>
            <ActionIcon variant="default" size="lg" aria-label="Инструменты аналитика">
              <IconDots size={20} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>Инструменты аналитика</Menu.Label>
            <Menu.Item leftSection={<IconBookmark size={17} />} onClick={() => openPanel('saved')}>
              Сохранённые кейсы ({state.saved.length})
            </Menu.Item>
            <Menu.Item
              leftSection={<IconColumns3 size={17} />}
              onClick={() => openPanel('comparison')}
            >
              Сравнение ({state.comparison.length}/3)
            </Menu.Item>
            <Menu.Item leftSection={<FocusIcon size={17} />} onClick={onPresentation}>
              {presentation ? 'Выйти из презентации' : 'Режим презентации'}
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item
              leftSection={<IconMoon size={17} />}
              onClick={() => setColorScheme(scheme === 'light' ? 'dark' : 'light')}
            >
              {scheme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Box>
    </>
  );
}
