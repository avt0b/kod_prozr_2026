import type { StylesheetJson } from 'cytoscape';
import {
  GRAPH_CARD_HEIGHT,
  GRAPH_CARD_WIDTH,
  GRAPH_ROOT_HEIGHT,
  GRAPH_ROOT_WIDTH,
} from './graphAppearance';

// Cytoscape owns layout, hit-testing and the camera. GraphVisual paints their output.
export const graphHitAreas: StylesheetJson = [
  {
    selector: 'node',
    style: {
      shape: 'round-rectangle',
      width: GRAPH_CARD_WIDTH,
      height: GRAPH_CARD_HEIGHT,
      'background-opacity': 0,
      'overlay-opacity': 0,
      'border-width': 0,
    },
  },
  {
    selector: 'node.root',
    style: { width: GRAPH_ROOT_WIDTH, height: GRAPH_ROOT_HEIGHT, 'z-index': 2 },
  },
  {
    selector: 'edge',
    style: { width: 1, 'line-opacity': 0, events: 'no', 'overlay-opacity': 0 },
  },
];
