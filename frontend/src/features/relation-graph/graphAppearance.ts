import type { GraphNodeType } from '@/shared/api';

export const GRAPH_APPEARANCE = {
  person: {
    color: '#0071e3',
    dark: '#94caff',
    path: 'M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0 M5 21v-2a4 4 0 0 1 4 -4h6a4 4 0 0 1 4 4v2',
  },
  company: {
    color: '#b66b00',
    dark: '#ffca86',
    path: 'M3 21h18 M5 21v-14l9 -4v18 M14 10h5v11 M8 10h2 M8 14h2 M8 18h2 M16 14h1 M16 18h1',
  },
  organ: {
    color: '#007f60',
    dark: '#8ae8c7',
    path: 'M3 9l9 -6l9 6z M4 21h16 M6 12v6 M12 12v6 M18 12v6',
  },
  contract: {
    color: '#8b40bc',
    dark: '#dfadff',
    path: 'M13 3H6a1 1 0 0 0 -1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1 -1V9z M13 3v6h6 M9 13h6 M9 17h6',
  },
  appeal: {
    color: '#007e89',
    dark: '#88e4e6',
    path: 'M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1 -1 1H4a1 1 0 0 1 -1 -1V6a1 1 0 0 1 1 -1z M3 7l9 6l9 -6',
  },
} satisfies Record<GraphNodeType, { color: string; dark: string; path: string }>;

export const GRAPH_CARD_WIDTH = 209;
export const GRAPH_ROOT_WIDTH = 245;
export const GRAPH_LABEL_WIDTH = 152;
