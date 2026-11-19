import {
  Anchor,
  Badge,
  Button,
  Card,
  Drawer,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useQueries } from '@tanstack/react-query';
import { IconBookmark, IconColumns3, IconX, IconPlus } from '@tabler/icons-react';
import { useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '@/shared/api';
import { officialsKeys } from '@/features/officials/api';
import { routes } from '@/shared/config/routes';
import { RULE_TITLES } from '@/shared/lib/labels';
import { QueryState, RiskScoreBadge } from '@/shared/ui';
import { useWorkbench } from './context';
import { CaseActions } from './CaseActions';
import { COMPARISON_LIMIT } from './model';
import { ComparisonPicker } from './ComparisonPicker';
import { RuleComparison } from './RuleComparison';

function EmptyCollection({ saved }: { saved: boolean }) {
  const { openPanel } = useWorkbench();
  const Icon = saved ? IconBookmark : IconColumns3;
  return (
    <div className="workbench-empty">
      <Icon size={44} stroke={1.3} />
      <Title order={3}>{saved ? 'Важные кейсы — под рукой' : 'Сравните картину целиком'}</Title>
      <Text c="dimmed">
        {saved
          ? 'Сохраните кейс кнопкой закладки в рейтинге или профиле. Он останется в списке на этом устройстве.'
          : 'Добавьте до трёх служащих кнопкой сравнения в рейтинге или профиле. Показатели загрузятся из API.'}
      </Text>
      <Button component={Link} to={routes.officials()} onClick={() => openPanel(null)}>
        Открыть рейтинг
      </Button>
    </div>
  );
}

function ComparisonContent() {
  const { state, toggleComparison, clearComparison, openPanel } = useWorkbench();
  const [adding, setAdding] = useState(false);
  const addRef = useRef<HTMLButtonElement>(null);
  const clearRef = useRef<HTMLButtonElement>(null);
  const full = state.comparison.length >= COMPARISON_LIMIT;
  const queries = useQueries({
    queries: state.comparison.map((item) => ({
      queryKey: officialsKeys.detail(item.id),
      queryFn: () => api.officials.get(item.id),
    })),
  });
  const allLoaded = queries.every((query) => query.isSuccess && query.data);
  const common =
    allLoaded && queries.length > 1
      ? [...new Set(queries[0].data!.risk.flags.map((flag) => flag.rule_code))].filter((code) =>
          queries.every((query) => query.data!.risk.flags.some((flag) => flag.rule_code === code)),
        )
      : [];
  const closePicker = () => {
    setAdding(false);
    if (full) clearRef.current?.focus();
    else addRef.current?.focus();
  };
  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Text c="dimmed" size="sm">
          {state.comparison.length} из 3 кейсов · текущие данные API
        </Text>
        <Group gap="sm">
          <Button
            ref={addRef}
            size="sm"
            leftSection={<IconPlus size={17} />}
            disabled={full}
            onClick={() => setAdding(true)}
          >
            Добавить служащего
          </Button>
          <Button
            ref={clearRef}
            size="xs"
            variant="subtle"
            color="gray"
            disabled={!state.comparison.length}
            onClick={clearComparison}
          >
            Очистить сравнение
          </Button>
        </Group>
      </Group>
      {full && (
        <Text size="sm" c="dimmed">
          Все три места заняты. Уберите кейс, чтобы добавить другого служащего.
        </Text>
      )}
      {adding && <ComparisonPicker onClose={closePicker} />}
      {allLoaded && queries.length > 1 && (
        <RuleComparison cases={state.comparison} profiles={queries.map((query) => query.data!)} />
      )}
      {!state.comparison.length ? (
        <EmptyCollection saved={false} />
      ) : (
        <SimpleGrid className="comparison-grid" cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
          {state.comparison.map((item, index) => (
            <Card key={item.id} className="comparison-case">
              <Group
                className="comparison-case-heading"
                justify="space-between"
                align="flex-start"
                wrap="nowrap"
              >
                <Title order={3}>{item.name}</Title>
                <Button
                  variant="subtle"
                  size="compact-xs"
                  color="gray"
                  aria-label={`Убрать из сравнения: ${item.name}`}
                  onClick={() => toggleComparison(item)}
                >
                  <IconX size={16} />
                </Button>
              </Group>
              <QueryState query={queries[index]}>
                {(profile) => (
                  <>
                    <Text className="comparison-case-organ" c="dimmed" size="sm" mt="sm">
                      {profile.appointments[0]?.organ.name ?? 'Орган не указан'}
                    </Text>
                    <div className="comparison-score">
                      <RiskScoreBadge score={profile.risk.score} size="xl" />
                      <span>балл риска из 100</span>
                    </div>
                    <dl className="comparison-metrics">
                      <div>
                        <dt>Флаги риска</dt>
                        <dd>{profile.risk.flags.length}</dd>
                      </div>
                      <div>
                        <dt>Высокий риск</dt>
                        <dd>
                          {profile.risk.flags.filter((flag) => flag.severity === 'high').length}
                        </dd>
                      </div>
                      <div>
                        <dt>Родственники</dt>
                        <dd>
                          {new Set(profile.relatives.map((relative) => relative.person.id)).size}
                        </dd>
                      </div>
                      <div>
                        <dt>Связанные компании</dt>
                        <dd>{new Set(profile.companies.map((link) => link.company.id)).size}</dd>
                      </div>
                    </dl>
                    <Group gap={6} mt="md">
                      {profile.risk.flags.map((flag) => (
                        <Badge
                          key={flag.id}
                          variant="light"
                          color={common.includes(flag.rule_code) ? 'brand' : 'gray'}
                          title={RULE_TITLES[flag.rule_code]}
                        >
                          {flag.rule_code}
                        </Badge>
                      ))}
                      {!profile.risk.flags.length && (
                        <Text c="dimmed" size="sm">
                          Флагов не выявлено
                        </Text>
                      )}
                    </Group>
                  </>
                )}
              </QueryState>
              <Anchor
                component={Link}
                to={routes.official(item.id)}
                onClick={() => openPanel(null)}
                mt="lg"
                size="sm"
              >
                Открыть профиль
              </Anchor>
            </Card>
          ))}
          {!full && (
            <button
              type="button"
              className="comparison-add"
              data-remaining={COMPARISON_LIMIT - state.comparison.length}
              onClick={() => setAdding(true)}
              aria-label="Выбрать ещё одного служащего"
            >
              <span>
                <IconPlus size={28} stroke={1.5} />
              </span>
              <strong>Добавить ещё</strong>
              <small>
                {state.comparison.length === 1
                  ? 'Ещё два места для сравнения'
                  : 'Ещё одно место для сравнения'}
              </small>
            </button>
          )}
        </SimpleGrid>
      )}
      <Text size="xs" c="dimmed">
        Балл и совпадение правил помогают сопоставить кейсы. Они не являются выводом о
        правонарушении.
      </Text>
    </Stack>
  );
}

export function WorkbenchPanels() {
  const { state, panel, openPanel } = useWorkbench();
  return (
    <>
      <Drawer
        opened={panel === 'saved'}
        onClose={() => openPanel(null)}
        title="Сохранённые кейсы"
        closeButtonProps={{ 'aria-label': 'Закрыть сохранённые кейсы' }}
        position="right"
        size="lg"
      >
        <Text c="dimmed" size="sm" mb="lg">
          На этом устройстве · список сохраняется в браузере
        </Text>
        {state.saved.length ? (
          <Stack gap="sm">
            {state.saved.map((item) => (
              <Card key={item.id} className="saved-case">
                <Group justify="space-between" wrap="nowrap">
                  <Anchor
                    component={Link}
                    to={routes.official(item.id)}
                    onClick={() => openPanel(null)}
                    fw={600}
                  >
                    {item.name}
                  </Anchor>
                  <CaseActions person={item} />
                </Group>
              </Card>
            ))}
          </Stack>
        ) : (
          <EmptyCollection saved />
        )}
        {state.comparison.length > 0 && (
          <Button
            fullWidth
            mt="lg"
            variant="light"
            leftSection={<IconColumns3 size={18} />}
            onClick={() => openPanel('comparison')}
          >
            Сравнить выбранные ({state.comparison.length})
          </Button>
        )}
      </Drawer>
      <Drawer
        opened={panel === 'comparison'}
        onClose={() => openPanel(null)}
        title="Сравнение служащих"
        closeButtonProps={{ 'aria-label': 'Закрыть сравнение' }}
        position="right"
        size="min(1140px, calc(100vw - 24px))"
      >
        {panel === 'comparison' && <ComparisonContent />}
      </Drawer>
    </>
  );
}
