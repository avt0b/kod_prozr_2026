import type { NodeSingular, StylesheetJson } from 'cytoscape';
import {
  GRAPH_APPEARANCE,
  GRAPH_CARD_WIDTH,
  GRAPH_LABEL_WIDTH,
  GRAPH_ROOT_WIDTH,
} from './graphAppearance';

const typeLabels = {
  person: 'ЛИЦО',
  company: 'КОМПАНИЯ',
  organ: 'ГОСУДАРСТВЕННЫЙ ОРГАН',
  contract: 'КОНТРАКТЫ',
  appeal: 'ОБРАЩЕНИЕ ГРАЖДАН',
} as const;

function cardIcon(path: string, tint: string, caption: string, width: number, height: number) {
  const size = height === 72 ? 43 : 38;
  const top = (height - size) / 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}">
    <rect x="10" y="${top}" width="${size}" height="${size}" rx="10" fill="${tint}" fill-opacity=".09" stroke="${tint}" stroke-opacity=".28"/>
    <path transform="translate(${10 + (size - 24) / 2} ${top + (size - 24) / 2})" d="${path}" fill="none" stroke="${tint}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="${20 + size}" y="${height === 72 ? 25 : 22}" fill="${tint}" font-family="monospace" font-size="8" font-weight="700" letter-spacing=".45">${caption}</text>
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export function buildStylesheet(dark: boolean): StylesheetJson {
  const ink = dark ? '#e9f1fc' : '#192436';
  const surface = dark ? '#182639' : '#fefefe';
  const border = dark ? '#3e536c' : '#cbd7e5';
  const accent = dark ? '#a0d3ff' : '#245fbb';
  const edge = dark ? '#69829f' : '#8298b2';
  const restHeight = 62;
  const rootHeight = 72;
  const rootTint = dark ? '#ff9a98' : '#e6322e';
  const { path: personIcon } = GRAPH_APPEARANCE.person;
  const iconRules: StylesheetJson = (
    Object.keys(GRAPH_APPEARANCE) as (keyof typeof GRAPH_APPEARANCE)[]
  ).map((type) => {
    const { color, dark: darkColor, path } = GRAPH_APPEARANCE[type];
    const tint = dark ? darkColor : color;
    return {
      selector: `node[type = "${type}"]`,
      style: {
        'background-image': cardIcon(path, tint, typeLabels[type], GRAPH_CARD_WIDTH, restHeight),
        'border-color': tint,
        'border-opacity': 0.35,
      },
    };
  });
  const edgeTones = [
    ['kinship', '#e6322e', '#ff9e96'],
    ['founder', '#bd7000', '#ffbc6c'],
    ['director', '#bd7000', '#ffbc6c'],
    ['employment', '#bd7000', '#ffbc6c'],
    ['works_in', '#008468', '#8be8c3'],
    ['supplier', '#8849bb', '#d6aaff'],
    ['customer', '#8849bb', '#d6aaff'],
    ['mentions', '#00828f', '#8ee7eb'],
    ['shared_contact', '#c64834', '#ffada0'],
  ] as const;

  return [
    {
      selector: 'node',
      style: {
        shape: 'round-rectangle',
        width: GRAPH_CARD_WIDTH,
        height: restHeight,
        label: 'data(cardLabel)',
        'font-size': 13,
        'font-weight': 600,
        color: ink,
        'font-family': 'system-ui, sans-serif',
        'text-valign': 'center',
        'text-margin-x': 21,
        'text-margin-y': 9,
        'text-wrap': 'wrap',
        'text-max-width': '146px',
        'background-color': surface,
        'background-width': '100%',
        'background-height': '100%',
        'border-width': 1,
        'border-color': border,
        'overlay-opacity': 0,
        'z-index': 3,
      },
    },
    ...iconRules,
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
    {
      selector: 'node.root',
      style: {
        width: GRAPH_ROOT_WIDTH,
        height: rootHeight,
        'background-color': dark ? '#253145' : surface,
        'background-image': (node: NodeSingular) => {
          const score = node.data('risk') as number | undefined;
          const label = Number.isFinite(score) ? `СЛУЖАЩИЙ · РИСК ${score}` : 'СЛУЖАЩИЙ · ФОКУС';
          return cardIcon(personIcon, rootTint, label, GRAPH_ROOT_WIDTH, rootHeight);
        },
        'border-width': 2,
        'border-color': rootTint,
        'border-opacity': 0.64,
        'text-max-width': '172px',
        'font-size': 15,
        'font-weight': 700,
        'underlay-color': rootTint,
        'underlay-shape': 'round-rectangle',
        'underlay-opacity': 0.17,
        'underlay-padding': 9,
      },
    },
    ...edgeTones.map(([type, light, night]) => {
      const tone = dark ? night : light;
      return {
        selector: `edge[type = "${type}"]`,
        style: {
          color: tone,
          'line-color': tone,
          'target-arrow-color': tone,
          'text-border-color': tone,
          'text-border-opacity': 0.35,
        },
      };
    }),
  ];
}
