import { Button, Group, Select, Stack, Textarea } from '@mantine/core';
import { useState } from 'react';
import type { AppealChannel, CreateAppealPayload } from '@/shared/api';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';

const EXAMPLE =
  'Начальник отдела закупок Министерства строительства Соколов А.В. 12 ноября 2026 года предложил нашей фирме «помочь» с победой в аукционе за 500 000 рублей.';

interface Props {
  submitting?: boolean;
  onSubmit: (payload: CreateAppealPayload) => void;
}

export function AppealForm({ submitting, onSubmit }: Props) {
  const [text, setText] = useState('');
  const [channel, setChannel] = useState<AppealChannel>('web');
  const tooShort = text.trim().length < 20;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!tooShort) onSubmit({ text: text.trim(), channel });
      }}
    >
      <Stack>
        <Select
          label="Канал поступления"
          data={Object.entries(APPEAL_CHANNEL_LABELS).map(([value, label]) => ({ value, label }))}
          value={channel}
          onChange={(v) => v && setChannel(v as AppealChannel)}
          allowDeselect={false}
          w={280}
        />
        <Textarea
          label="Текст обращения"
          description="Минимум 20 символов. После отправки обращение будет автоматически проанализировано."
          autosize
          minRows={6}
          maxRows={16}
          value={text}
          onChange={(e) => setText(e.currentTarget.value)}
          required
        />
        <Group justify="space-between">
          <Button variant="subtle" onClick={() => setText(EXAMPLE)}>
            Вставить пример
          </Button>
          <Button type="submit" loading={submitting} disabled={tooShort}>
            Отправить на анализ
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
