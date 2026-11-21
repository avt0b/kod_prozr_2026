import { useState, type FormEvent } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { IconMoon, IconShieldSearch, IconSun } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AccountMenu } from '@/features/auth/AccountMenu';
import { api, type AppealStatus } from '@/shared/api';
import { formatDateTime } from '@/shared/lib/format';
import { QueryState } from '@/shared/ui';
import './citizen.css';

const MIN_LENGTH = 20;
const MAX_LENGTH = 20_000;

/** Статусы глазами гражданина: без внутренних терминов анализа. */
const CITIZEN_STATUS: Record<AppealStatus, { label: string; color: string; hint: string }> = {
  new: { label: 'Принято', color: 'gray', hint: 'Обращение зарегистрировано.' },
  analyzed: {
    label: 'На рассмотрении',
    color: 'blue',
    hint: 'Аналитик изучает обращение.',
  },
  routed: {
    label: 'Передано по подведомственности',
    color: 'violet',
    hint: 'Обращение направлено в ведомство, уполномоченное его рассмотреть.',
  },
  closed: { label: 'Рассмотрено', color: 'green', hint: 'Рассмотрение завершено.' },
};

const MY_APPEALS = ['citizen', 'appeals'] as const;

function ThemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme('light');
  return (
    <Tooltip label="Сменить тему">
      <ActionIcon
        variant="default"
        size={40}
        aria-label="Сменить тему"
        onClick={() => setColorScheme(computed === 'light' ? 'dark' : 'light')}
      >
        {computed === 'light' ? <IconMoon size={18} /> : <IconSun size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

function AppealForm() {
  const client = useQueryClient();
  const [text, setText] = useState('');
  const submit = useMutation({
    mutationFn: (value: string) => api.citizen.submit(value),
    retry: false,
    onSuccess: () => {
      setText('');
      void client.invalidateQueries({ queryKey: MY_APPEALS });
    },
  });
  const length = text.trim().length;
  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (length >= MIN_LENGTH) submit.mutate(text.trim());
  }
  return (
    <Card component="form" className="citizen-card" onSubmit={onSubmit}>
      <Stack gap="md">
        <div>
          <Title order={2} size="h3">
            Новое обращение
          </Title>
          <Text c="dimmed" size="sm" mt={4}>
            Опишите ситуацию: кто, где и когда, о каком нарушении идёт речь. Чем конкретнее
            сведения, тем быстрее обращение рассмотрят.
          </Text>
        </div>
        {submit.isSuccess && (
          <Alert color="green" role="status" title="Обращение отправлено">
            Оно появилось в списке ниже. Статус меняется по мере рассмотрения.
          </Alert>
        )}
        {submit.isError && (
          <Alert color="red" role="alert" title="Не удалось отправить обращение">
            {submit.error.message}
          </Alert>
        )}
        <Textarea
          label="Текст обращения"
          required
          autosize
          minRows={6}
          maxRows={16}
          maxLength={MAX_LENGTH}
          value={text}
          onChange={(event) => setText(event.currentTarget.value)}
          description={`Не меньше ${MIN_LENGTH} символов`}
          error={length > 0 && length < MIN_LENGTH ? 'Опишите ситуацию подробнее' : undefined}
        />
        <Group justify="space-between">
          <Text size="xs" c="dimmed">
            {length.toLocaleString('ru-RU')} / {MAX_LENGTH.toLocaleString('ru-RU')}
          </Text>
          <Button type="submit" loading={submit.isPending} disabled={length < MIN_LENGTH}>
            Отправить
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

function MyAppeals() {
  const appeals = useQuery({
    queryKey: [...MY_APPEALS],
    queryFn: () => api.citizen.appeals({ limit: 50 }),
  });
  return (
    <Stack gap="sm">
      <Title order={2} size="h3">
        Мои обращения
      </Title>
      <QueryState
        query={appeals}
        isEmpty={(page) => page.items.length === 0}
        empty={
          <Text c="dimmed" size="sm">
            Вы ещё не подавали обращений.
          </Text>
        }
      >
        {(page) => (
          <Stack gap="sm">
            {page.items.map((appeal) => {
              const status = CITIZEN_STATUS[appeal.status];
              return (
                <Card key={appeal.id} className="citizen-card" data-testid="citizen-appeal">
                  <Group justify="space-between" align="flex-start" wrap="wrap" gap="xs">
                    <Text size="sm" c="dimmed">
                      {formatDateTime(appeal.received_at)}
                    </Text>
                    <Tooltip label={status.hint}>
                      <Badge color={status.color} variant="light">
                        {status.label}
                      </Badge>
                    </Tooltip>
                  </Group>
                  <Text mt="xs" className="citizen-appeal-text" lineClamp={4}>
                    {appeal.text}
                  </Text>
                </Card>
              );
            })}
          </Stack>
        )}
      </QueryState>
    </Stack>
  );
}

export function CitizenPage() {
  return (
    <div className="citizen-page">
      <header className="citizen-header">
        <Group gap="sm" wrap="nowrap">
          <span className="workspace-brand-mark">
            <IconShieldSearch size={21} aria-hidden />
          </span>
          <div>
            <Text fw={600}>Код прозрачности</Text>
            <Text size="xs" c="dimmed">
              Кабинет гражданина
            </Text>
          </div>
        </Group>
        <Group gap="xs" wrap="nowrap">
          <ThemeToggle />
          <AccountMenu />
        </Group>
      </header>
      <main className="citizen-main">
        <Stack gap="xl">
          <div>
            <Title order={1}>Сообщить о коррупции</Title>
            <Text c="dimmed" mt="xs">
              Обращение получит аналитик. Ваши данные не передаются лицам, указанным в обращении.
            </Text>
          </div>
          <AppealForm />
          <MyAppeals />
        </Stack>
      </main>
    </div>
  );
}
