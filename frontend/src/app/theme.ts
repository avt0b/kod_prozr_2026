import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Combobox,
  createTheme,
  Drawer,
  type CSSVariablesResolver,
  type MantineColorsTuple,
  Modal,
  Notification,
  NumberInput,
  Paper,
  Popover,
  Select,
  Table,
  Textarea,
  TextInput,
} from '@mantine/core';

const brand: MantineColorsTuple = [
  '#edf3ff',
  '#dce8ff',
  '#bacfff',
  '#92b3f5',
  '#7099ed',
  '#497ce0',
  '#2b65d2',
  '#2456ba',
  '#1c469b',
  '#163979',
];

const surface = {
  defaultProps: { withBorder: true, radius: 'lg' },
  classNames: { root: 'workspace-surface' },
};
const field = { classNames: { input: 'workspace-field' } };
const control = { classNames: { root: 'workspace-control' } };

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
  radius: { xs: '6px', sm: '9px', md: '13px', lg: '21px', xl: '28px' },
  fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
  fontFamilyMonospace: 'ui-monospace, SFMono-Regular, Consolas, monospace',
  headings: { fontWeight: '735' },
  components: {
    Card: Card.extend({ ...surface, defaultProps: { ...surface.defaultProps, padding: 'lg' } }),
    Paper: Paper.extend(surface),
    Button: Button.extend(control),
    ActionIcon: ActionIcon.extend(control),
    TextInput: TextInput.extend(field),
    NumberInput: NumberInput.extend(field),
    Textarea: Textarea.extend(field),
    Select: Select.extend(field),
    Alert: Alert.extend({ defaultProps: { radius: 'lg' } }),
    Table: Table.extend({
      defaultProps: { verticalSpacing: 'sm', highlightOnHover: true },
      classNames: { table: 'workspace-table', thead: 'workspace-table-head' },
    }),
    Combobox: Combobox.extend({ classNames: { dropdown: 'workspace-popover' } }),
    Popover: Popover.extend({ classNames: { dropdown: 'workspace-popover' } }),
    Drawer: Drawer.extend({
      classNames: { content: 'workspace-popover', header: 'workspace-drawer-header' },
    }),
    Modal: Modal.extend({
      defaultProps: { radius: 'lg' },
      classNames: { content: 'workspace-popover', header: 'workspace-drawer-header' },
    }),
    Notification: Notification.extend({ classNames: { root: 'workspace-popover' } }),
  },
});
