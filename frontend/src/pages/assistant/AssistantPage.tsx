import { Card } from '@mantine/core';
import { AssistantChat } from '@/features/assistant/AssistantChat';
import { PageHeader } from '@/shared/ui';

export function AssistantPage() {
  return (
    <>
      <PageHeader
        title="Ассистент аналитика"
        description="Вопросы на естественном языке к данным о служащих, связях и обращениях. Ответ содержит ссылки на источники."
      />
      <Card maw={960}>
        <AssistantChat />
      </Card>
    </>
  );
}
