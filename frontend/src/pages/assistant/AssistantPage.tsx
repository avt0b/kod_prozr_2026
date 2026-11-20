import { useLocation } from 'react-router';
import { AssistantChat } from '@/features/assistant/AssistantChat';
import { PageHeader } from '@/shared/ui';

export function AssistantPage() {
  const { state } = useLocation();
  const initialDraft = typeof state?.draft === 'string' ? (state.draft as string) : '';
  return (
    <>
      <PageHeader title="Ассистент аналитика" description="Поиск по данным и связям" />
      <AssistantChat initialDraft={initialDraft} />
    </>
  );
}
