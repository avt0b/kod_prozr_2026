import { createContext, useContext } from 'react';
import type { CaseRef, WorkbenchState } from './model';

export type WorkbenchPanel = 'saved' | 'comparison' | null;
export interface WorkbenchContextValue {
  state: WorkbenchState;
  panel: WorkbenchPanel;
  openPanel: (panel: WorkbenchPanel) => void;
  toggleSaved: (item: CaseRef) => void;
  toggleComparison: (item: CaseRef) => void;
  clearComparison: () => void;
}
export const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);
export function useWorkbench() {
  const value = useContext(WorkbenchContext);
  if (!value) throw new Error('WorkbenchProvider is missing');
  return value;
}
