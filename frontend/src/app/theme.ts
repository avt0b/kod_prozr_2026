import { createTheme, type MantineColorsTuple } from '@mantine/core';

// Основной синий из docs/variants.html (#1D3F9E)
const brand: MantineColorsTuple = [
  '#ebf0fd',
  '#d3dcf4',
  '#a4b6eb',
  '#728de2',
  '#4a6bdb',
  '#3156d7',
  '#234bd6',
  '#163cbe',
  '#1D3F9E',
  '#00287e',
];

export const theme = createTheme({
  primaryColor: 'brand',
  colors: { brand },
  primaryShade: { light: 8, dark: 4 },
  defaultRadius: 'md',
  fontFamily: 'Inter, "Segoe UI", system-ui, -apple-system, sans-serif',
  fontFamilyMonospace: '"JetBrains Mono", ui-monospace, SFMono-Regular, Consolas, monospace',
  headings: { fontWeight: '600' },
  components: {
    Card: { defaultProps: { withBorder: true, radius: 'md', padding: 'lg' } },
    Paper: { defaultProps: { withBorder: true } },
    Table: { defaultProps: { verticalSpacing: 'sm', highlightOnHover: true } },
  },
});
