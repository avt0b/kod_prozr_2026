import type { StylesheetJson } from 'cytoscape';
import type { GraphNodeType } from '@/shared/api';

/** Цвет и форма узла по типу. Используется и в стилях Cytoscape, и в легенде. */
export const NODE_STYLES: Record<GraphNodeType, { color: string; shape: string }> = {
  person: { color: '#1D3F9E', shape: 'ellipse' },
  company: { color: '#E8590C', shape: 'round-rectangle' },
  organ: { color: '#2B8A3E', shape: 'hexagon' },
  contract: { color: '#7048E8', shape: 'diamond' },
  appeal: { color: '#E67700', shape: 'tag' },
};

export function buildStylesheet(dark: boolean): StylesheetJson {
  const text = dark ? '#F0F5FB' : '#172636';
  const edge = dark ? '#627D99' : '#93A6BA';
  const textBg = dark ? '#192636' : '#FFFFFF';
  const selection = dark ? '#87B6F5' : '#2D65A8';

  return [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'font-size': 13,
        color: text,
        'text-valign': 'bottom',
        'text-margin-y': 4,
        'text-wrap': 'wrap',
        'text-max-width': '140px',
        'text-background-color': textBg,
        'text-background-opacity': 0.8,
        'text-background-padding': '2px',
        width: 26,
        height: 26,
        'border-width': 0,
      },
    },
    ...(Object.entries(NODE_STYLES).map(([type, s]) => ({
      selector: `node[type = "${type}"]`,
      style: { 'background-color': s.color, shape: s.shape },
    })) as StylesheetJson),
    { selector: 'node[type = "contract"]', style: { width: 26, height: 26, 'font-size': 12 } },
    { selector: 'node[risk >= 70]', style: { 'border-width': 4, 'border-color': '#E03131' } },
    {
      selector: 'node[risk > 0][risk < 40]',
      style: { 'border-width': 2, 'border-color': '#2F9E44' },
    },
    {
      selector: 'node[risk >= 40][risk < 70]',
      style: { 'border-width': 3, 'border-color': '#F76707' },
    },
    {
      selector: 'node.root',
      style: { width: 42, height: 42, 'font-size': 12, 'font-weight': 'bold' },
    },
    {
      selector: 'edge',
      style: {
        width: 1.5,
        'line-color': edge,
        'target-arrow-color': edge,
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.8,
        'curve-style': 'bezier',
        label: 'data(label)',
        'font-size': 10,
        color: dark ? '#94A2BC' : '#5B6A86',
        'text-rotation': 'autorotate',
        'text-background-color': textBg,
        'text-background-opacity': 0.8,
      },
    },
    {
      selector: 'edge[type = "kinship"]',
      style: { 'line-style': 'dashed', 'target-arrow-shape': 'none' },
    },
    { selector: '.faded', style: { opacity: 0.18 } },
    {
      selector: 'node.hl',
      style: {
        shape: 'round-rectangle',
        width: 130,
        height: 54,
        label: 'data(cardLabel)',
        'background-color': textBg,
        'border-width': 1.5,
        'border-color': selection,
        'text-valign': 'center',
        'text-margin-y': 0,
        'text-max-width': '118px',
        'text-wrap': 'wrap',
        'text-background-opacity': 0,
        'font-size': 12,
        'z-index': 2,
      },
    },
    {
      selector: 'edge.hl',
      style: { width: 3, 'line-color': selection, 'target-arrow-color': selection, opacity: 1 },
    },
  ];
}
