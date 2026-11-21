import { useEffect, useState, useSyncExternalStore, type FormEvent } from 'react';
import {
  Alert,
  Anchor,
  Button,
  Paper,
  PasswordInput,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { Navigate, useLocation } from 'react-router';
import {
  getSnapshot,
  homeOf,
  login,
  refreshSession,
  register,
  ROLE_LABELS,
  subscribe,
  type Role,
} from '@/shared/lib/authSession';
import './auth.css';
import { DEMO_ACCOUNTS } from '@/shared/config/demoAccount';
import { usePageTitle } from '@/shared/lib/usePageTitle';

type Mode = 'login' | 'register';

/** Возврат на исходный маршрут, только если он доступен роли (#70). */
function destinationFor(role: Role, from: unknown): string {
  if (
    typeof from !== 'string' ||
    !from.startsWith('/') ||
    from.startsWith('//') ||
    from.startsWith('/login')
  )
    return homeOf(role);
  const citizenPath = from === '/citizen' || from.startsWith('/citizen/');
  if (role === 'citizen' ? !citizenPath : citizenPath) return homeOf(role);
  if (role !== 'admin' && from.startsWith('/admin')) return homeOf(role);
  return from;
}

export function LoginPage() {
  const { user, ready } = useSyncExternalStore(subscribe, getSnapshot);
  const location = useLocation();
  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  usePageTitle(mode === 'register' ? 'Регистрация · Код прозрачности' : 'Вход · Код прозрачности');
  useEffect(() => {
    if (!ready) void refreshSession();
  }, [ready]);
  if (user) {
    const from: unknown = (location.state as { from?: unknown } | null)?.from;
    return <Navigate to={destinationFor(user.role, from)} replace />;
  }
  const registering = mode === 'register';
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (registering && password !== confirm) {
      setError('Пароли не совпадают.');
      return;
    }
    setBusy(true);
    try {
      if (registering) await register(username.trim(), password);
      else await login(username.trim(), password);
      setPassword('');
      setConfirm('');
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
            <SegmentedControl
              fullWidth
              value={mode}
              onChange={(value) => {
                setMode(value as Mode);
                setError('');
              }}
              data={[
                { value: 'login', label: 'Вход' },
                { value: 'register', label: 'Регистрация' },
              ]}
              aria-label="Вход или регистрация"
            />
            <div>
              <Title order={1} size="h2">
                {registering ? 'Регистрация гражданина' : 'Вход в кабинет'}
              </Title>
              <Text c="dimmed" mt="xs">
                {registering
                  ? 'Учётная запись нужна, чтобы подать обращение и следить за его статусом.'
                  : 'Граждане входят в личный кабинет, сотрудники — в рабочее место.'}
              </Text>
            </div>
            {error && (
              <Alert color="red" role="alert">
                {error}
              </Alert>
            )}
            <TextInput
              label="Логин"
              description={registering ? 'Латинские буквы, цифры, «_», «.», «-»' : undefined}
              autoComplete="username"
              required
              minLength={registering ? 3 : undefined}
              maxLength={64}
              value={username}
              onChange={(event) => setUsername(event.currentTarget.value)}
              autoFocus
            />
            <PasswordInput
              classNames={{ input: 'workspace-field' }}
              visibilityToggleButtonProps={{ 'aria-label': 'Показать или скрыть пароль' }}
              label="Пароль"
              description={registering ? 'Не меньше 12 символов' : undefined}
              autoComplete={registering ? 'new-password' : 'current-password'}
              required
              minLength={registering ? 12 : undefined}
              maxLength={256}
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
            />
            {registering && (
              <PasswordInput
                classNames={{ input: 'workspace-field' }}
                visibilityToggleButtonProps={{ 'aria-label': 'Показать или скрыть пароль' }}
                label="Повторите пароль"
                autoComplete="new-password"
                required
                maxLength={256}
                value={confirm}
                onChange={(event) => setConfirm(event.currentTarget.value)}
              />
            )}
            <Button type="submit" loading={busy} disabled={!ready} fullWidth>
              {registering ? 'Зарегистрироваться' : 'Войти'}
            </Button>
            {!registering && (
              <Stack gap={6}>
                <Text size="sm" c="dimmed">
                  Быстрый вход на тестовом стенде
                </Text>
                <Stack gap={6}>
                  {(Object.keys(DEMO_ACCOUNTS) as Role[]).map((role) => (
                    <Button
                      key={role}
                      type="button"
                      variant="light"
                      size="sm"
                      fullWidth
                      justify="space-between"
                      rightSection={
                        <span className="auth-quick-login" aria-hidden>
                          {DEMO_ACCOUNTS[role].username}
                        </span>
                      }
                      disabled={busy}
                      onClick={() => {
                        setUsername(DEMO_ACCOUNTS[role].username);
                        setPassword(DEMO_ACCOUNTS[role].password);
                        setError('');
                      }}
                    >
                      {ROLE_LABELS[role]}
                    </Button>
                  ))}
                </Stack>
              </Stack>
            )}
          </Stack>
        </Paper>
        <Text size="sm" c="dimmed" mt="lg">
          {registering ? (
            <>
              Уже есть учётная запись?{' '}
              <Anchor component="button" type="button" onClick={() => setMode('login')}>
                Войти
              </Anchor>
            </>
          ) : (
            'Учётные записи сотрудников выдаёт администратор.'
          )}
        </Text>
      </div>
    </main>
  );
}
