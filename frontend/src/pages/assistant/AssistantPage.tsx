import { AssistantChat } from '@/features/assistant/AssistantChat';
import { PageHeader } from '@/shared/ui';

export function AssistantPage() {
  return (
    <>
      <PageHeader title="Ассистент аналитика" description="Поиск по данным и связям" />
      <AssistantChat />
    </>
  );
}
