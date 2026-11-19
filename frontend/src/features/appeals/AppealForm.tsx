import { Alert, Button, Group, Select, Stack, Textarea } from '@mantine/core';
import { useState } from 'react';
import type { AppealChannel, CreateAppealPayload } from '@/shared/api';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';

import { DEMO_APPEAL } from './demoAppeal';

interface Props {
  submitting?: boolean;
  onSubmit: (payload: CreateAppealPayload) => void;
}

export function AppealForm({ submitting, onSubmit }: Props) {
  const [text, setText] = useState('');
  const [channel, setChannel] = useState<AppealChannel>('web');
  const tooShort = text.trim().length < 20;
  const tooLong = Array.from(text.trim()).length > 20_000;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!tooShort && !tooLong && !submitting) onSubmit({ text: text.trim(), channel });
      }}
    >
      <Stack>
        <Select
          label="Канал поступления"
          data={Object.entries(APPEAL_CHANNEL_LABELS).map(([value, label]) => ({ value, label }))}
          value={channel}
          onChange={(v) => v && setChannel(v as AppealChannel)}
          allowDeselect={false}
          disabled={submitting}
          w={280}
        />
        <Textarea
          label="Текст обращения"
          description="Минимум 20 символов. После отправки обращение будет автоматически проанализировано."
          autosize
          minRows={8}
          maxRows={16}
          value={text}
          onChange={(e) => setText(e.currentTarget.value)}
          required
          disabled={submitting}
          error={tooLong ? 'Максимум 20 000 символов' : undefined}
        />
        {submitting && (
          <Alert title="Обращение анализируется" role="status">
            Обычно это занимает 5–15 секунд. Проверяем категорию, сущности и связи со служащими.
          </Alert>
        )}
        <Group justify="space-between">
          <Button
            type="button"
            variant="subtle"
            disabled={submitting}
            onClick={() => setText(DEMO_APPEAL)}
          >
            Вставить пример
          </Button>
          <Button type="submit" loading={submitting} disabled={tooShort || tooLong}>
            Отправить на анализ
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
