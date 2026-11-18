import {
  ActionIcon,
  Alert,
  Button,
  Card,
  CloseButton,
  Combobox,
  createTheme,
  Drawer,
  type CSSVariablesResolver,
  type MantineColorsTuple,
  Modal,
  Notification,
  NumberInput,
  Paper,
  Pagination,
  Popover,
  SegmentedControl,
  Select,
  Switch,
  Table,
  Textarea,
  TextInput,
} from '@mantine/core';

const brand: MantineColorsTuple = [
  '#eaf2ff',
  '#dce9fb',
  '#b8d2f4',
  '#98bcef',
  '#75a1d9',
  '#5486c6',
  '#356ab1',
  '#194f9b',
  '#164583',
  '#123564',
];

const surface = {
  defaultProps: { withBorder: true, radius: 'lg' },
  classNames: { root: 'workspace-surface' },
};
const field = { classNames: { input: 'workspace-field' } };
const control = { defaultProps: { radius: 'xl' }, classNames: { root: 'workspace-control' } };
const easeOut = 'cubic-bezier(0.2, 0.8, 0.2, 1)';
const anchoredTransition = {
  transition: 'pop-top-left',
  duration: 180,
  exitDuration: 120,
  timingFunction: easeOut,
} as const;
const panelTransition = {
  duration: 220,
  exitDuration: 180,
  timingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
};
const panelClassNames = { content: 'workspace-popover', header: 'workspace-drawer-header' };
const overlayProps = { backgroundOpacity: 0.29, blur: 6 };

const semanticColors = {
  '--mantine-color-text': 'var(--workspace-ink)',
  '--mantine-color-dimmed': 'var(--workspace-muted)',
  '--mantine-color-default-border': 'var(--workspace-edge)',
  '--mantine-color-body': 'var(--workspace-sky)',
};

export const workspaceVariables: CSSVariablesResolver = () => ({
  variables: {},
  light: semanticColors,
  dark: semanticColors,
});

export const theme = createTheme({
  primaryColor: 'brand',
  colors: { brand },
  primaryShade: { light: 7, dark: 7 },
  defaultRadius: 'md',
  respectReducedMotion: true,
  radius: { xs: '6px', sm: '9px', md: '13px', lg: '16px', xl: '28px' },
  fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
  fontFamilyMonospace: 'ui-monospace, SFMono-Regular, Consolas, monospace',
  headings: { fontWeight: '735' },
  components: {
    Card: Card.extend({ ...surface, defaultProps: { ...surface.defaultProps, padding: 'lg' } }),
    Paper: Paper.extend(surface),
    Button: Button.extend({
      ...control,
      defaultProps: { ...control.defaultProps, variant: 'filled' },
    }),
    ActionIcon: ActionIcon.extend(control),
    CloseButton: CloseButton.extend(control),
    Pagination: Pagination.extend({
      defaultProps: { radius: 'xl' },
      classNames: { control: 'workspace-control workspace-page-control' },
    }),
    SegmentedControl: SegmentedControl.extend({
      defaultProps: { radius: 'xl', transitionDuration: 180, transitionTimingFunction: easeOut },
      classNames: { root: 'workspace-segmented', indicator: 'workspace-segment-indicator' },
    }),
    Switch: Switch.extend({
      classNames: { track: 'workspace-switch-track', thumb: 'workspace-switch-thumb' },
    }),
    TextInput: TextInput.extend(field),
    NumberInput: NumberInput.extend(field),
    Textarea: Textarea.extend(field),
    Select: Select.extend({
      classNames: { ...field.classNames, dropdown: 'workspace-popover workspace-dropdown' },
      defaultProps: { comboboxProps: { transitionProps: anchoredTransition } },
    }),
    Alert: Alert.extend({ defaultProps: { radius: 'lg' } }),
    Table: Table.extend({
      defaultProps: { verticalSpacing: 'sm', highlightOnHover: true },
      classNames: { table: 'workspace-table', thead: 'workspace-table-head' },
    }),
    Combobox: Combobox.extend({
      defaultProps: { transitionProps: anchoredTransition },
      classNames: { dropdown: 'workspace-popover workspace-dropdown' },
    }),
    Popover: Popover.extend({
      defaultProps: { transitionProps: anchoredTransition },
      classNames: { dropdown: 'workspace-popover workspace-dropdown' },
    }),
    Drawer: Drawer.extend({
      defaultProps: { transitionProps: panelTransition, overlayProps },
      classNames: { ...panelClassNames, content: 'workspace-popover workspace-drawer' },
    }),
    Modal: Modal.extend({
      defaultProps: { radius: 'lg', transitionProps: anchoredTransition, overlayProps },
      classNames: panelClassNames,
    }),
    Notification: Notification.extend({ classNames: { root: 'workspace-popover' } }),
  },
});
