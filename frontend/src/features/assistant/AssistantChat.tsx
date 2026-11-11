import {
  ActionIcon,
  Anchor,
  Badge,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { IconSend } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { AssistantSource } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { useAskAssistant } from './api';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  sources?: AssistantSource[];
  error?: boolean;
}

const SUGGESTIONS = [
  'Покажи служащих, у которых родственники среди подрядчиков их органа',
  'Сколько обращений о взятках?',
  'Кто в зоне наибольшего риска?',
];

const SOURCE_LABELS: Record<AssistantSource['type'], string> = {
  person: 'служащий',
  company: 'компания',
  organ: 'орган',
  contract: 'контракт',
  appeal: 'обращение',
  flag: 'флаг',
};

/** Ссылка на источник: где есть своя страница — ведём туда. */
function sourceHref(s: AssistantSource): string | null {
  if (s.type === 'person') return routes.official(s.id);
  if (s.type === 'appeal') return routes.appeal(s.id);
  return null;
}

function SourceList({ sources }: { sources: AssistantSource[] }) {
  return (
    <Stack gap={2} mt="xs">
      <Text size="xs" c="dimmed">
        Источники:
      </Text>
      {sources.map((s) => {
        const href = sourceHref(s);
        return (
          <Group key={`${s.type}-${s.id}`} gap={6} wrap="nowrap">
            <Badge size="xs" variant="light" color="gray">
              {SOURCE_LABELS[s.type]}
            </Badge>
            {href ? (
              <Anchor component={Link} to={href} size="xs">
                {s.label}
              </Anchor>
            ) : (
              <Text size="xs">{s.label}</Text>
            )}
          </Group>
        );
      })}
    </Stack>
  );
}

export function AssistantChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const ask = useAskAssistant();

  const send = (question: string) => {
    const q = question.trim();
    if (!q || ask.isPending) return;
    setMessages((m) => [...m, { id: Date.now(), role: 'user', text: q }]);
    setDraft('');
    ask.mutate(q, {
      onSuccess: (res) =>
        setMessages((m) => [
          ...m,
          { id: Date.now(), role: 'assistant', text: res.answer, sources: res.sources },
        ]),
      onError: (e) =>
        setMessages((m) => [
          ...m,
          { id: Date.now(), role: 'assistant', text: `Ошибка: ${e.message}`, error: true },
        ]),
    });
  };

  return (
    <Stack gap="md">
      <ScrollArea h="calc(100vh - 330px)" mih={300} type="auto">
        <Stack gap="sm" pr="sm">
          {messages.length === 0 && (
            <Stack gap="xs">
              <Text c="dimmed" size="sm">
                Задайте вопрос на естественном языке. Например:
              </Text>
              {SUGGESTIONS.map((s) => (
                <Anchor key={s} size="sm" component="button" type="button" onClick={() => send(s)}>
                  {s}
                </Anchor>
              ))}
            </Stack>
          )}
          {messages.map((m) => (
            <Paper
              key={m.id}
              p="md"
              maw="85%"
              ml={m.role === 'user' ? 'auto' : undefined}
              bg={m.role === 'user' ? 'var(--mantine-primary-color-light)' : undefined}
              style={m.error ? { borderColor: 'var(--mantine-color-red-6)' } : undefined}
            >
              <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                {m.text}
              </Text>
              {m.sources && m.sources.length > 0 && <SourceList sources={m.sources} />}
            </Paper>
          ))}
          {ask.isPending && <Loader size="sm" type="dots" />}
        </Stack>
      </ScrollArea>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <Group align="flex-end" wrap="nowrap">
          <Textarea
            style={{ flex: 1 }}
            placeholder="Ваш вопрос… (Enter — отправить, Shift+Enter — перенос строки)"
            autosize
            minRows={1}
            maxRows={5}
            value={draft}
            onChange={(e) => setDraft(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send(draft);
              }
            }}
          />
          <ActionIcon type="submit" size="xl" loading={ask.isPending} aria-label="Отправить">
            <IconSend size={20} />
          </ActionIcon>
        </Group>
      </form>
    </Stack>
  );
}
