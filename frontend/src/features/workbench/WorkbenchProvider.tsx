import { useLocalStorage } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useState, type ReactNode } from 'react';
import { WorkbenchContext, type WorkbenchPanel } from './context';
import {
  COMPARISON_LIMIT,
  SAVED_LIMIT,
  EMPTY_WORKBENCH,
  decodeWorkbench,
  toggleCase,
  type CaseRef,
  type WorkbenchState,
} from './model';

export function WorkbenchProvider({ children, userId }: { children: ReactNode; userId: string }) {
  const [state, setState] = useLocalStorage<WorkbenchState>({
    key: `kod-prozr:workbench:v1:${userId}`,
    defaultValue: EMPTY_WORKBENCH,
    getInitialValueInEffect: false,
    deserialize: decodeWorkbench,
  });
  const [panel, openPanel] = useState<WorkbenchPanel>(null);
  const toggleSaved = (item: CaseRef) => {
    if (
      state.saved.length >= SAVED_LIMIT &&
      !state.saved.some((current) => current.id === item.id)
    ) {
      notifications.show({
        color: 'orange',
        message: 'Сохранено 50 кейсов. Уберите один, чтобы добавить новый.',
      });
      return;
    }
    setState((previous) => ({ ...previous, saved: toggleCase(previous.saved, item, SAVED_LIMIT) }));
  };
  const toggleComparison = (item: CaseRef) => {
    if (
      state.comparison.length >= COMPARISON_LIMIT &&
      !state.comparison.some((current) => current.id === item.id)
    ) {
      notifications.show({
        color: 'orange',
        message: 'В сравнении уже три кейса. Уберите один, чтобы добавить новый.',
      });
      return;
    }
    setState((previous) => ({
      ...previous,
      comparison: toggleCase(previous.comparison, item, COMPARISON_LIMIT),
    }));
  };
  return (
    <WorkbenchContext.Provider
      value={{
        state,
        panel,
        openPanel,
        toggleSaved,
        toggleComparison,
        clearComparison: () => setState((previous) => ({ ...previous, comparison: [] })),
      }}
    >
      {children}
    </WorkbenchContext.Provider>
  );
}
