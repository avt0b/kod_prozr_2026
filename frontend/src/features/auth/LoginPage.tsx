import { useEffect, useState, useSyncExternalStore, type FormEvent } from 'react';
import { Alert, Button, Paper, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { Navigate, useLocation } from 'react-router';
import { getSnapshot, login, refreshSession, subscribe } from '@/shared/lib/authSession';
import './auth.css';

export function LoginPage() {
  const { user, ready } = useSyncExternalStore(subscribe, getSnapshot);
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!ready) void refreshSession();
  }, [ready]);
  const from: unknown = (location.state as { from?: unknown } | null)?.from;
  const destination =
    typeof from === 'string' &&
    from.startsWith('/') &&
    !from.startsWith('//') &&
    !from.startsWith('/login')
      ? from
      : '/';
  if (user) return <Navigate to={destination} replace />;
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username.trim(), password);
      setPassword('');
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Не удалось войти.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <div className="auth-container">
        <Text className="auth-brand">Код прозрачности</Text>
        <Paper component="form" className="auth-form" onSubmit={submit}>
          <Stack gap="lg">
            <div>
              <Title order={1} size="h2">
                Вход в кабинет
              </Title>
              <Text c="dimmed" mt="xs">
                Используйте учётную запись, выданную администратором.
              </Text>
            </div>
            {error && (
              <Alert color="red" role="alert">
                {error}
              </Alert>
            )}
            <TextInput
              label="Логин"
              autoComplete="username"
              required
              maxLength={64}
              value={username}
              onChange={(event) => setUsername(event.currentTarget.value)}
              autoFocus
            />
            <PasswordInput
              classNames={{ input: 'workspace-field' }}
              visibilityToggleButtonProps={{ 'aria-label': 'Показать или скрыть пароль' }}
              label="Пароль"
              autoComplete="current-password"
              required
              maxLength={256}
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
            />
            <Button type="submit" loading={busy} disabled={!ready} fullWidth>
              Войти
            </Button>
          </Stack>
        </Paper>
        <Text size="sm" c="dimmed" mt="lg">
          Доступ предоставляется сотрудникам, работающим с проверкой данных.
        </Text>
      </div>
    </main>
  );
}
