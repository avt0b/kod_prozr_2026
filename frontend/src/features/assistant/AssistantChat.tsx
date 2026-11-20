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
import { IconSend, IconNetwork, IconChartBar, IconMail } from '@tabler/icons-react';
import { useReducedMotion } from '@mantine/hooks';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import type { AssistantSource } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { useAskAssistant } from './api';
import { AlexeyMascot } from './AlexeyMascot';
import { hasProfanity } from './mascotMood';
import { useAnswerReveal } from './useAnswerReveal';

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
  const reducedMotion = useReducedMotion();
  const { playback, reveal } = useAnswerReveal(reducedMotion);
  const busy = ask.isPending || Boolean(playback);
  const [seat, setSeat] = useState<HTMLDivElement | null>(null);
  const [caret, setCaret] = useState<number>();
  const composer = useRef<HTMLTextAreaElement>(null);
  const answerText = useRef<HTMLSpanElement>(null);
  const nextId = useRef(0);
  const typingEnd = useRef<number>();
  const endRef = useRef<HTMLDivElement>(null);
  const lastMessage = messages.at(-1);

  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: 'instant', block: 'nearest' });
  }, [messages, ask.isPending]);
  useEffect(() => () => window.clearTimeout(typingEnd.current), []);

  const stopTyping = () => {
    window.clearTimeout(typingEnd.current);
    setCaret(undefined);
  };

  const send = (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    const user: Message = { id: nextId.current++, role: 'user', text: q };
    setMessages((previous) => [...previous, user]);
    setDraft('');
    stopTyping();
    ask.mutate(q, {
      onSuccess: (res) => {
        const answer: Message = {
          id: nextId.current++,
          role: 'assistant',
          text: res.answer,
          sources: res.sources,
        };
        setMessages((previous) => [...previous, answer]);
        reveal(answer.id, answer.text);
      },
      onError: (error) => {
        const failure: Message = {
          id: nextId.current++,
          role: 'assistant',
          text: `Ошибка: ${error.message}`,
          error: true,
        };
        setMessages((previous) => [...previous, failure]);
      },
    });
  };

  return (
    <div className="assistant-workspace" data-has-messages={messages.length > 0 || undefined}>
      <div
        className="assistant-conversation"
        role="log"
        aria-label="Диалог с ассистентом"
        aria-live="polite"
        aria-busy={busy}
      >
        <AlexeyMascot
          seat={seat}
          reducedMotion={reducedMotion}
          annoyed={hasProfanity(draft)}
          gaze={
            playback
              ? { kind: 'speaking', answer: answerText, glyph: playback.glyph }
              : ask.isPending
                ? { kind: 'waiting' }
                : draft.trim() && caret !== undefined
                  ? { kind: 'typing', field: composer, caret }
                  : { kind: 'idle' }
          }
        />
        <Stack gap="lg">
          {messages.length === 0 && (
            <div className="assistant-welcome">
              <div className="assistant-alexey-welcome-seat" ref={setSeat} aria-hidden="true" />
              <span className="editorial-eyebrow">Ассистент аналитика</span>
              <h1>
                <span className="motion-headline-line">Ваш вопрос.</span>
                <span className="motion-headline-line">Проверяемые источники.</span>
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
          {messages.map((m) => {
            const current = m.role === 'assistant' && m.id === lastMessage?.id;
            const writing = playback?.id === m.id ? playback : undefined;
            const bubble = (
              <Paper
                key={m.id}
                className={`assistant-message assistant-message-${m.role}`}
                p="md"
                maw={current ? undefined : { base: '94%', sm: '76%' }}
                ml={m.role === 'user' ? 'auto' : undefined}
                bg={m.role === 'user' ? 'var(--workspace-tint)' : 'var(--workspace-neutral)'}
                style={m.error ? { borderColor: 'var(--mantine-color-red-6)' } : undefined}
              >
                <Text size="xs" fw={600} c="dimmed" mb="xs">
                  {m.role === 'user' ? 'Вы' : 'Алексей'}
                </Text>
                <Text className="assistant-alexey-copy">
                  <span
                    ref={current ? answerText : undefined}
                    aria-hidden={writing ? true : undefined}
                  >
                    {writing?.text ?? m.text}
                  </span>
                </Text>
                {!writing && m.sources && m.sources.length > 0 && (
                  <SourceList sources={m.sources} />
                )}
              </Paper>
            );
            return current ? (
              <div key={m.id} className="assistant-animated-turn">
                <div className="assistant-alexey-reply-seat" ref={setSeat} aria-hidden="true" />
                {bubble}
              </div>
            ) : (
              bubble
            );
          })}
          {ask.isPending && (
            <div className="assistant-animated-turn">
              <div className="assistant-alexey-reply-seat" ref={setSeat} aria-hidden="true" />
              <Group role="status" className="assistant-alexey-wait" gap="xs">
                <Loader size="sm" type="dots" />
                <Text size="sm" c="dimmed">
                  Проверяю данные и источники…
                </Text>
              </Group>
            </div>
          )}
          <div ref={endRef} />
        </Stack>
      </div>

      <form
        className="assistant-composer workspace-glass"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <Group align="flex-end" wrap="nowrap">
          <Textarea
            ref={composer}
            style={{ flex: 1 }}
            placeholder="Спросите о служащих, связях или обращениях…"
            aria-label="Вопрос ассистенту"
            autosize
            minRows={1}
            maxRows={5}
            value={draft}
            onChange={(e) => {
              setDraft(e.currentTarget.value);
              setCaret(e.currentTarget.selectionEnd);
              window.clearTimeout(typingEnd.current);
              typingEnd.current = window.setTimeout(() => setCaret(undefined), 1600);
            }}
            onBlur={stopTyping}
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
            disabled={busy || !draft.trim()}
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
