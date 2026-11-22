import { useState, type FormEvent } from 'react';
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  MultiSelect,
  Select,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { IconPlus, IconShare } from '@tabler/icons-react';
import type { GraphNodeType, OfficialGraph } from '@/shared/api';
import { request, type HttpMethod } from '@/shared/api/client';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';
import { QueryState } from '@/shared/ui';
import type { Workspace, WorkspaceController, WorkspaceUser } from './api';
import './manualGraph.css';

function Shares({
  workspace,
  controller,
}: {
  workspace: Workspace;
  controller: WorkspaceController;
}) {
  const [selected, setSelected] = useState(workspace.shared_with.map((user) => user.id));
  const [search, setSearch] = useState('');
  const [usersOpened, setUsersOpened] = useState(false);
  const [query] = useDebouncedValue(search, 250);
  const [message, setMessage] = useState('');
  const users = useQuery({
    queryKey: ['workspace-users', query],
    queryFn: () => request<WorkspaceUser[]>('GET', '/graph-workspaces/users', { query: { query } }),
    enabled: workspace.can_edit,
  });
  const options = [
    ...new Map(
      [...workspace.shared_with, ...(users.data ?? [])].map((user) => [
        user.id,
        { value: user.id, label: user.username },
      ]),
    ).values(),
  ];
  return (
    <Stack gap="md">
      <Text size="sm">
        Выбранные пользователи смогут открыть схему и просматривать ваши объекты и связи. Право
        изменения остаётся у владельца.
      </Text>
      {workspace.can_edit ? (
        <>
          {users.isError && (
            <Alert color="red">
              Не удалось загрузить пользователей.{' '}
              <Anchor onClick={() => void users.refetch()}>Повторить</Anchor>
            </Alert>
          )}
          <MultiSelect
            label="Кому дать доступ"
            data={options}
            value={selected}
            onChange={(values) => {
              setSelected(values);
              setUsersOpened(false);
            }}
            dropdownOpened={usersOpened}
            onDropdownOpen={() => setUsersOpened(true)}
            onDropdownClose={() => setUsersOpened(false)}
            searchable
            searchValue={search}
            onSearchChange={setSearch}
            maxValues={30}
            placeholder="Выберите пользователей"
            nothingFoundMessage="Пользователи не найдены"
          />
          <Button
            loading={controller.mutation.isPending}
            onClick={async () => {
              setMessage('');
              try {
                await controller.mutation.mutateAsync({
                  method: 'PUT',
                  path: `/graph-workspaces/${workspace.id}/shares`,
                  body: { user_ids: selected },
                });
                setMessage('Доступ сохранён');
              } catch {
                setMessage('Не удалось сохранить доступ. Повторите попытку.');
              }
            }}
          >
            Сохранить доступ
          </Button>
        </>
      ) : (
        <Text size="sm">Владелец схемы — {workspace.owner_name}. Вам доступен просмотр.</Text>
      )}
      <Button
        variant="default"
        leftSection={<IconShare size={16} />}
        onClick={async () => {
          try {
            const url = new URL(window.location.href);
            url.searchParams.set('scheme', workspace.id);
            await navigator.clipboard.writeText(url.toString());
            setMessage('Ссылка скопирована. Для открытия нужен выданный доступ.');
          } catch {
            setMessage('Не удалось скопировать ссылку. Скопируйте адрес из строки браузера.');
          }
        }}
      >
        Скопировать ссылку
      </Button>
      {message && (
        <Text role="status" size="sm">
          {message}
        </Text>
      )}
    </Stack>
  );
}

export function ManualGraphEditor({
  controller,
  baseGraph,
}: {
  controller: WorkspaceController;
  baseGraph?: OfficialGraph;
}) {
  const [opened, setOpened] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('Моя схема');
  const [kind, setKind] = useState<GraphNodeType>('person');
  const [label, setLabel] = useState('');
  const [notes, setNotes] = useState('');
  const [source, setSource] = useState('');
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [edgeLabel, setEdgeLabel] = useState('');
  const [edgeNotes, setEdgeNotes] = useState('');
  const [edgeSource, setEdgeSource] = useState('');
  const [error, setError] = useState('');
  const workspace = controller.workspace;
  const busy = controller.mutation.isPending;
  const editable = Boolean(workspace?.can_edit);
  const nodes = [
    ...(baseGraph?.nodes.map((node) => ({
      value: node.id,
      label: `${NODE_TYPE_LABELS[node.type]}: ${node.label.replaceAll('\n', ' ')}`,
    })) ?? []),
    ...(workspace?.nodes.map((node) => ({ value: node.id, label: `Вручную: ${node.label}` })) ??
      []),
  ];
  const names = new Map(nodes.map((node) => [node.value, node.label]));
  async function run(method: HttpMethod, path: string, body?: unknown) {
    setError('');
    try {
      return await controller.mutation.mutateAsync({ method, path, body });
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Не удалось сохранить изменения.');
      return undefined;
    }
  }
  async function addNode(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    if (
      await run('POST', `/graph-workspaces/${workspace.id}/nodes`, { kind, label, notes, source })
    ) {
      setLabel('');
      setNotes('');
      setSource('');
    }
  }
  async function addEdge(event: FormEvent) {
    event.preventDefault();
    if (!workspace || !from || !to) return;
    if (
      await run('POST', `/graph-workspaces/${workspace.id}/edges`, {
        source_id: from,
        target_id: to,
        label: edgeLabel,
        notes: edgeNotes,
        source: edgeSource,
      })
    ) {
      setEdgeLabel('');
      setEdgeNotes('');
      setEdgeSource('');
    }
  }
  return (
    <>
      <Button
        className="manual-graph-launcher"
        variant="default"
        leftSection={<IconPlus size={17} />}
        onClick={() => setOpened(true)}
      >
        Дополнить граф
      </Button>
      <Drawer
        opened={opened}
        onClose={() => setOpened(false)}
        position="right"
        size="lg"
        title="Дополнение графа"
        closeButtonProps={{ 'aria-label': 'Закрыть редактор графа' }}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Ручные сведения — отдельный аналитический слой. Они не подтверждают нарушение и не
            меняют балл риска.
          </Text>
          <QueryState query={controller.list}>
            {(items) => (
              <Select
                label="Аналитическая схема"
                disabled={busy}
                clearable
                placeholder="Исходный граф без дополнений"
                value={controller.activeId}
                data={items.map((item) => ({
                  value: item.id,
                  label: `${item.title} · ${item.can_edit ? 'моя' : item.owner_name}`,
                }))}
                onChange={(id) => {
                  controller.select(id);
                  setError('');
                  setCreating(false);
                }}
              />
            )}
          </QueryState>
          <Button variant="light" disabled={busy} onClick={() => setCreating((value) => !value)}>
            Новая схема
          </Button>
          {creating && (
            <form
              onSubmit={async (event) => {
                event.preventDefault();
                const created = await run('POST', '/graph-workspaces', {
                  official_id: controller.officialId,
                  title,
                });
                if (created) setCreating(false);
              }}
            >
              <Stack gap="sm">
                <TextInput
                  label="Название схемы"
                  value={title}
                  onChange={(event) => setTitle(event.currentTarget.value)}
                  required
                  minLength={1}
                  maxLength={120}
                />
                <Button type="submit" loading={busy}>
                  Создать схему
                </Button>
              </Stack>
            </form>
          )}
          {error && (
            <Alert color="red" role="alert">
              {error}
            </Alert>
          )}
          {controller.activeId && (
            <QueryState query={controller.detail}>
              {(data) =>
                data.official_id !== controller.officialId ? (
                  <Alert color="red">Эта схема относится к другому служащему.</Alert>
                ) : (
                  <>
                    <Group justify="space-between">
                      <Title order={3} size="h5">
                        {data.title}
                      </Title>
                      <Badge variant="light">
                        {data.can_edit ? 'Моя схема' : 'Только просмотр'}
                      </Badge>
                    </Group>
                    <Tabs defaultValue="nodes" key={data.id}>
                      <Tabs.List grow>
                        <Tabs.Tab value="nodes">Объекты</Tabs.Tab>
                        <Tabs.Tab value="edges">Связи</Tabs.Tab>
                        <Tabs.Tab value="share">Доступ</Tabs.Tab>
                      </Tabs.List>
                      <Tabs.Panel value="nodes" pt="md">
                        <Stack gap="md">
                          {editable && (
                            <form onSubmit={addNode}>
                              <Stack gap="sm">
                                <Select
                                  label="Тип объекта"
                                  value={kind}
                                  allowDeselect={false}
                                  data={Object.entries(NODE_TYPE_LABELS).map(([value, label]) => ({
                                    value,
                                    label,
                                  }))}
                                  onChange={(value) => value && setKind(value as GraphNodeType)}
                                />
                                <TextInput
                                  label="Название объекта"
                                  required
                                  maxLength={200}
                                  value={label}
                                  onChange={(event) => setLabel(event.currentTarget.value)}
                                />
                                <Textarea
                                  label="Пояснение к объекту"
                                  maxLength={2000}
                                  value={notes}
                                  onChange={(event) => setNotes(event.currentTarget.value)}
                                />
                                <TextInput
                                  label="Источник сведений об объекте"
                                  maxLength={500}
                                  value={source}
                                  onChange={(event) => setSource(event.currentTarget.value)}
                                  placeholder="Документ, ссылка или описание"
                                />
                                <Button type="submit" loading={busy}>
                                  Добавить объект
                                </Button>
                              </Stack>
                            </form>
                          )}
                          <Divider />
                          {!data.nodes.length && (
                            <Text size="sm" c="dimmed">
                              Ручные объекты пока не добавлены.
                            </Text>
                          )}
                          {data.nodes.map((node) => (
                            <div className="manual-record" key={node.id}>
                              <Text fw={600}>{node.label}</Text>
                              <Text size="xs" c="dimmed">
                                {NODE_TYPE_LABELS[node.kind]} · внесено аналитиком
                              </Text>
                              {node.notes && <Text size="sm">{node.notes}</Text>}
                              {node.source && <Text size="xs">Источник: {node.source}</Text>}
                              {editable && (
                                <Button
                                  variant="subtle"
                                  color="red"
                                  size="xs"
                                  disabled={busy}
                                  aria-label={`Удалить объект: ${node.label}`}
                                  onClick={() =>
                                    void run(
                                      'DELETE',
                                      `/graph-workspaces/${data.id}/nodes/${node.id}`,
                                    )
                                  }
                                >
                                  Удалить объект и его связи
                                </Button>
                              )}
                            </div>
                          ))}
                        </Stack>
                      </Tabs.Panel>
                      <Tabs.Panel value="edges" pt="md">
                        <Stack gap="md">
                          {editable && (
                            <form onSubmit={addEdge}>
                              <Stack gap="sm">
                                <Select
                                  label="От какого объекта"
                                  searchable
                                  required
                                  data={nodes}
                                  value={from}
                                  onChange={setFrom}
                                />
                                <Select
                                  label="К какому объекту"
                                  searchable
                                  required
                                  data={nodes.filter((node) => node.value !== from)}
                                  value={to}
                                  onChange={setTo}
                                />
                                <TextInput
                                  label="Название связи"
                                  required
                                  maxLength={160}
                                  value={edgeLabel}
                                  onChange={(event) => setEdgeLabel(event.currentTarget.value)}
                                  placeholder="Например: совместный проект"
                                />
                                <Textarea
                                  label="Пояснение к связи"
                                  maxLength={2000}
                                  value={edgeNotes}
                                  onChange={(event) => setEdgeNotes(event.currentTarget.value)}
                                />
                                <TextInput
                                  label="Источник сведений о связи"
                                  maxLength={500}
                                  value={edgeSource}
                                  onChange={(event) => setEdgeSource(event.currentTarget.value)}
                                />
                                <Button
                                  type="submit"
                                  loading={busy}
                                  disabled={!from || !to || from === to || !baseGraph}
                                >
                                  Добавить связь
                                </Button>
                              </Stack>
                            </form>
                          )}
                          {!data.edges.length && (
                            <Text size="sm" c="dimmed">
                              Ручные связи пока не добавлены.
                            </Text>
                          )}
                          {data.edges.map((edge) => (
                            <div className="manual-record" key={edge.id}>
                              <Text fw={600}>{edge.label}</Text>
                              <Text size="sm">
                                {names.get(edge.source_id) ?? 'Объект исходного графа'} →{' '}
                                {names.get(edge.target_id) ?? 'Объект исходного графа'}
                              </Text>
                              {edge.notes && <Text size="sm">{edge.notes}</Text>}
                              {edge.source && <Text size="xs">Источник: {edge.source}</Text>}
                              {editable && (
                                <Button
                                  variant="subtle"
                                  color="red"
                                  size="xs"
                                  disabled={busy}
                                  aria-label={`Удалить связь: ${edge.label}`}
                                  onClick={() =>
                                    void run(
                                      'DELETE',
                                      `/graph-workspaces/${data.id}/edges/${edge.id}`,
                                    )
                                  }
                                >
                                  Удалить связь
                                </Button>
                              )}
                            </div>
                          ))}
                        </Stack>
                      </Tabs.Panel>
                      <Tabs.Panel value="share" pt="md">
                        <Shares key={data.id} workspace={data} controller={controller} />
                      </Tabs.Panel>
                    </Tabs>
                    {editable && (
                      <Button
                        color="red"
                        variant="subtle"
                        disabled={busy}
                        onClick={async () => {
                          if (
                            !window.confirm(
                              'Удалить эту схему со всеми ручными объектами и связями?',
                            )
                          )
                            return;
                          setError('');
                          try {
                            await controller.mutation.mutateAsync({
                              method: 'DELETE',
                              path: `/graph-workspaces/${data.id}`,
                            });
                            controller.select(null);
                          } catch (problem) {
                            setError(
                              problem instanceof Error
                                ? problem.message
                                : 'Не удалось удалить схему.',
                            );
                          }
                        }}
                      >
                        Удалить схему
                      </Button>
                    )}
                  </>
                )
              }
            </QueryState>
          )}
        </Stack>
      </Drawer>
    </>
  );
}
