import { useState, useSyncExternalStore, type FormEvent } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconKey, IconLock, IconLockOpen, IconTrash, IconUserPlus } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type AdminUser, type AdminUserUpdate } from '@/shared/api';
import { getSnapshot, ROLE_LABELS, subscribe, type Role } from '@/shared/lib/authSession';
import { PageHeader, QueryState } from '@/shared/ui';

const USERS = ['admin', 'users'] as const;
const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as Role[]).map((value) => ({
  value,
  label: ROLE_LABELS[value],
}));

function useInvalidateUsers() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: USERS });
}

function CreateUserForm() {
  const invalidate = useInvalidateUsers();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('analyst');
  const create = useMutation({
    mutationFn: () => api.admin.create({ username: username.trim(), password, role }),
    retry: false,
    onSuccess: () => {
      setUsername('');
      setPassword('');
      void invalidate();
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  return (
    <Card component="form" onSubmit={submit}>
      <Stack gap="sm">
        <Title order={3} size="h4">
          Новая учётная запись
        </Title>
        {create.isError && (
          <Alert color="red" role="alert">
            {create.error.message}
          </Alert>
        )}
        {create.isSuccess && (
          <Alert color="green" role="status">
            Учётная запись {create.data.username} создана.
          </Alert>
        )}
        <Group align="flex-end" grow wrap="wrap">
          <TextInput
            label="Логин"
            required
            minLength={3}
            maxLength={64}
            pattern="[a-zA-Z0-9_.\-]+"
            value={username}
            onChange={(event) => setUsername(event.currentTarget.value)}
          />
          <PasswordInput
            label="Пароль"
            description="Не меньше 12 символов"
            required
            minLength={12}
            maxLength={256}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
          />
          <Select
            label="Роль"
            data={ROLE_OPTIONS}
            value={role}
            allowDeselect={false}
            onChange={(value) => value && setRole(value as Role)}
          />
        </Group>
        <Group justify="flex-end">
          <Button type="submit" leftSection={<IconUserPlus size={16} />} loading={create.isPending}>
            Создать
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

function PasswordModal({ user, onClose }: { user: AdminUser | null; onClose: () => void }) {
  const invalidate = useInvalidateUsers();
  const [password, setPassword] = useState('');
  const reset = useMutation({
    mutationFn: (id: string) => api.admin.update(id, { password }),
    retry: false,
    onSuccess: () => {
      setPassword('');
      void invalidate();
      onClose();
    },
  });
  return (
    <Modal
      opened={user !== null}
      onClose={onClose}
      title={`Новый пароль для ${user?.username ?? ''}`}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (user) reset.mutate(user.id);
        }}
      >
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Все сессии пользователя будут завершены.
          </Text>
          {reset.isError && (
            <Alert color="red" role="alert">
              {reset.error.message}
            </Alert>
          )}
          <PasswordInput
            label="Пароль"
            description="Не меньше 12 символов"
            required
            minLength={12}
            maxLength={256}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            data-autofocus
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Отмена
            </Button>
            <Button type="submit" loading={reset.isPending}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function UsersTable({ users }: { users: AdminUser[] }) {
  const { user: me } = useSyncExternalStore(subscribe, getSnapshot);
  const invalidate = useInvalidateUsers();
  const [passwordFor, setPasswordFor] = useState<AdminUser | null>(null);
  const [error, setError] = useState('');
  const onError = (problem: Error) => setError(problem.message);
  const onSuccess = () => {
    setError('');
    void invalidate();
  };
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: AdminUserUpdate }) =>
      api.admin.update(id, patch),
    retry: false,
    onSuccess,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.admin.remove(id),
    retry: false,
    onSuccess,
    onError,
  });
  const busy = update.isPending || remove.isPending;
  return (
    <>
      {error && (
        <Alert color="red" role="alert" mb="sm" withCloseButton onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      <Table.ScrollContainer minWidth={640}>
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Логин</Table.Th>
              <Table.Th>Роль</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th aria-label="Действия" />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((user) => {
              const self = user.id === me?.id;
              return (
                <Table.Tr key={user.id} data-testid="admin-user-row">
                  <Table.Td>
                    <Text fw={500}>{user.username}</Text>
                    {self && (
                      <Text size="xs" c="dimmed">
                        это вы
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Select
                      aria-label={`Роль ${user.username}`}
                      data={ROLE_OPTIONS}
                      value={user.role}
                      allowDeselect={false}
                      disabled={busy}
                      w={180}
                      onChange={(value) =>
                        value &&
                        value !== user.role &&
                        update.mutate({ id: user.id, patch: { role: value as Role } })
                      }
                    />
                  </Table.Td>
                  <Table.Td>
                    <Badge color={user.active ? 'green' : 'gray'} variant="light">
                      {user.active ? 'Активен' : 'Заблокирован'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={6} justify="flex-end" wrap="nowrap">
                      <Button
                        size="xs"
                        variant="light"
                        color={user.active ? 'orange' : 'green'}
                        leftSection={
                          user.active ? <IconLock size={14} /> : <IconLockOpen size={14} />
                        }
                        disabled={busy}
                        onClick={() =>
                          update.mutate({ id: user.id, patch: { active: !user.active } })
                        }
                      >
                        {user.active ? 'Заблокировать' : 'Разблокировать'}
                      </Button>
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconKey size={14} />}
                        disabled={busy}
                        onClick={() => setPasswordFor(user)}
                      >
                        Пароль
                      </Button>
                      <Button
                        size="xs"
                        variant="light"
                        color="red"
                        leftSection={<IconTrash size={14} />}
                        disabled={busy}
                        onClick={() => {
                          if (window.confirm(`Удалить учётную запись ${user.username}?`))
                            remove.mutate(user.id);
                        }}
                      >
                        Удалить
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <PasswordModal user={passwordFor} onClose={() => setPasswordFor(null)} />
    </>
  );
}

export function AdminUsersPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [search, setSearch] = useState('');
  const [query] = useDebouncedValue(search.trim(), 250);
  const users = useQuery({
    queryKey: [...USERS, role, query],
    queryFn: () =>
      api.admin.users({ role: role ?? undefined, query: query || undefined, limit: 200 }),
  });
  return (
    <>
      <PageHeader
        title="Пользователи"
        description="Аналитики, администраторы и граждане. Смена роли, блокировка и новый пароль сразу завершают сессии пользователя."
      />
      <Stack gap="lg">
        <CreateUserForm />
        <Card>
          <Group mb="md" grow wrap="wrap">
            <TextInput
              label="Поиск по логину"
              value={search}
              onChange={(event) => setSearch(event.currentTarget.value)}
            />
            <Select
              label="Роль"
              placeholder="Все роли"
              data={ROLE_OPTIONS}
              value={role}
              clearable
              onChange={(value) => setRole(value as Role | null)}
            />
          </Group>
          <QueryState
            query={users}
            isEmpty={(page) => page.items.length === 0}
            empty={
              <Text c="dimmed" size="sm">
                Никого не нашли.
              </Text>
            }
          >
            {(page) => <UsersTable users={page.items} />}
          </QueryState>
        </Card>
      </Stack>
    </>
  );
}
