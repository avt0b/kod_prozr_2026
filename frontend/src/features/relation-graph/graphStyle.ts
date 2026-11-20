import type { StylesheetJson } from 'cytoscape';
import {
  GRAPH_APPEARANCE,
  GRAPH_CARD_WIDTH,
  GRAPH_LABEL_WIDTH,
  GRAPH_ROOT_WIDTH,
} from './graphAppearance';

export function buildStylesheet(dark: boolean): StylesheetJson {
  const ink = dark ? '#e9f1fc' : '#192436';
  const surface = dark ? '#182639' : '#ffffff';
  const border = dark ? '#3e536c' : '#cbd7e5';
  const accent = dark ? '#a0d3ff' : '#245fbb';
  const edge = dark ? '#69829f' : '#8298b2';
  const iconRules: StylesheetJson = Object.entries(GRAPH_APPEARANCE).map(
    ([type, { color, dark: darkColor, path }]) => {
      const tint = dark ? darkColor : color;
      const icon =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
        `<rect width="32" height="32" rx="9" fill="${tint}" fill-opacity="0.13"/>` +
        `<path transform="translate(6 6) scale(.83)" d="${path}" fill="none" stroke="${tint}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
      return {
        selector: `node[type = "${type}"]`,
        style: { 'background-image': `data:image/svg+xml,${encodeURIComponent(icon)}` },
      };
    },
  );

  return [
    {
      selector: 'node',
      style: {
        shape: 'round-rectangle',
        width: GRAPH_CARD_WIDTH,
        height: 54,
        label: 'data(cardLabel)',
        'font-size': 13,
        'font-weight': 600,
        color: ink,
        'font-family': 'system-ui, sans-serif',
        'text-valign': 'center',
        'text-margin-x': 19,
        'text-wrap': 'wrap',
        'text-max-width': '111px',
        'background-color': surface,
        'background-width': 32,
        'background-height': 32,
        'background-position-x': '9px',
        'border-width': 1,
        'border-color': border,
        'overlay-opacity': 0,
        'z-index': 3,
      },
    },
    ...iconRules,
    {
      selector: 'node.root',
      style: {
        width: GRAPH_ROOT_WIDTH,
        height: 64,
        'background-color': dark ? '#213450' : '#eaf3ff',
        'border-width': 2,
        'border-color': accent,
        'text-max-width': '124px',
        'font-weight': 700,
        'underlay-color': accent,
        'underlay-shape': 'round-rectangle',
        'underlay-opacity': 0.12,
        'underlay-padding': 7,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 1.3,
        'line-color': edge,
        'target-arrow-color': edge,
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.7,
        'curve-style': 'bezier',
        'control-point-step-size': 64,
        label: 'data(label)',
        color: ink,
        'font-family': 'system-ui, sans-serif',
        'font-size': 12,
        'font-weight': 500,
        'text-rotation': 'none',
        'text-wrap': 'wrap',
        'text-max-width': `${GRAPH_LABEL_WIDTH}px`,
        'text-background-color': surface,
        'text-background-opacity': 1,
        'text-background-padding': '4px',
        'text-background-shape': 'roundrectangle',
        'text-border-color': border,
        'text-border-width': 1,
        'text-border-opacity': 0.9,
        'min-zoomed-font-size': 7,
      },
    },
    {
      selector: 'edge[type = "kinship"]',
      style: { 'line-style': 'dashed', 'target-arrow-shape': 'none' },
    },
    {
      selector: 'node.faded',
      style: { label: '', opacity: 0.2, 'z-index': 0 },
    },
    { selector: 'edge.faded', style: { label: '', opacity: 0.1, 'z-index': 0 } },
    {
      selector: 'node.hl, node.active-node',
      style: { 'border-color': accent, 'border-width': 2, opacity: 1, 'z-index': 5 },
    },
    {
      selector: 'node.active-node',
      style: { 'background-color': dark ? '#25405c' : '#dfeeff', 'border-width': 3 },
    },
    {
      selector: 'edge.hl',
      style: {
        width: 2.5,
        color: accent,
        'font-size': 13,
        'font-weight': 700,
        'line-color': accent,
        'target-arrow-color': accent,
        'text-border-color': accent,
        'min-zoomed-font-size': 0,
        'z-index': 2,
      },
    },
  ];
}
