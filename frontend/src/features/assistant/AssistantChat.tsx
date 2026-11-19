import {
  ActionIcon,
  Anchor,
  Badge,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import {
  IconSend,
  IconFingerprint,
  IconNetwork,
  IconChartBar,
  IconMail,
} from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
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
  {
    icon: IconNetwork,
    title: 'Найти скрытые связи',
    detail: 'Родственники среди подрядчиков',
    question: 'Покажи служащих, у которых родственники среди подрядчиков их органа',
  },
  {
    icon: IconMail,
    title: 'Изучить обращения',
    detail: 'Сообщения о взятках',
    question: 'Сколько обращений о взятках?',
  },
  {
    icon: IconChartBar,
    title: 'Определить приоритет',
    detail: 'Служащие с наибольшим риском',
    question: 'Кто в зоне наибольшего риска?',
  },
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
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: 'instant', block: 'nearest' });
  }, [messages, ask.isPending]);

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
    <div className="assistant-workspace" data-has-messages={messages.length > 0 || undefined}>
      <div
        className="assistant-conversation"
        role="log"
        aria-label="Диалог с ассистентом"
        aria-live="polite"
        aria-busy={ask.isPending}
      >
        <Stack gap="lg">
          {messages.length === 0 && (
            <div className="assistant-welcome">
              <div className="assistant-emblem" aria-hidden="true">
                <IconFingerprint size={48} stroke={1.25} />
              </div>
              <span className="editorial-eyebrow">Ассистент аналитика</span>
              <h1>
                Ваш вопрос.
                <br />
                <span>Проверяемые источники.</span>
              </h1>
              <p>
                Находите связи и задавайте вопросы к данным.
                <br />В ответе — факты и ссылки для проверки.
              </p>
              <div className="assistant-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.title}
                    type="button"
                    aria-label={`${s.title}. ${s.question}`}
                    onClick={() => send(s.question)}
                  >
                    <s.icon size={23} stroke={1.5} />
                    <strong>{s.title}</strong>
                    <span>{s.detail}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <Paper
              key={m.id}
              className={`assistant-message assistant-message-${m.role}`}
              p="md"
              maw="85%"
              ml={m.role === 'user' ? 'auto' : undefined}
              bg={m.role === 'user' ? 'var(--mantine-primary-color-light)' : undefined}
              style={m.error ? { borderColor: 'var(--mantine-color-red-6)' } : undefined}
            >
              <Text size="xs" fw={600} c="dimmed" mb="xs">
                {m.role === 'user' ? 'Вы' : 'Ассистент'}
              </Text>
              <Text style={{ whiteSpace: 'pre-wrap' }}>{m.text}</Text>
              {m.sources && m.sources.length > 0 && <SourceList sources={m.sources} />}
            </Paper>
          ))}
          {ask.isPending && (
            <Group role="status">
              <Loader size="sm" type="dots" />
              <Text size="sm" c="dimmed">
                Проверяю данные и источники…
              </Text>
            </Group>
          )}
          <div ref={endRef} />
        </Stack>
      </div>

      <form
        className="assistant-composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <Group align="flex-end" wrap="nowrap">
          <Textarea
            style={{ flex: 1 }}
            placeholder="Спросите о служащих, связях или обращениях…"
            aria-label="Вопрос ассистенту"
            autosize
            minRows={1}
            maxRows={5}
            value={draft}
            onChange={(e) => setDraft(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send(draft);
              }
            }}
          />
          <ActionIcon
            type="submit"
            size="xl"
            loading={ask.isPending}
            disabled={!draft.trim()}
            aria-label="Отправить"
          >
            <IconSend size={20} />
          </ActionIcon>
        </Group>
        <Text size="xs" c="dimmed" mt="sm">
          Enter — отправить · Shift + Enter — новая строка. Ответы требуют проверки аналитиком.
        </Text>
      </form>
    </div>
  );
}
