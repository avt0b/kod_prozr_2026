import { Badge, Card, Group, Stack, Table, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import type { OfficialProfile } from '@/shared/api';
import { formatDate, formatMoneyShort, formatPeriod } from '@/shared/lib/format';
import { AUTHORITY_LABELS, COMPANY_ROLE_LABELS, KINSHIP_LABELS } from '@/shared/lib/labels';

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <Title order={4} mb="sm">
        {title}
      </Title>
      {children}
    </Card>
  );
}

const Empty = () => (
  <Text size="sm" c="dimmed">
    нет данных
  </Text>
);

export function AppointmentsSection({ profile }: { profile: OfficialProfile }) {
  return (
    <Section title="Должности">
      {profile.appointments.length === 0 && <Empty />}
      <Stack gap="sm">
        {profile.appointments.map((a) => (
          <div key={a.id}>
            <Group gap="xs">
              <Text fw={500} size="sm">
                {a.position.title}, {a.position.department.toLowerCase()}
              </Text>
              {a.position.is_corruption_risky && (
                <Badge size="xs" color="orange" variant="light">
                  коррупционно-опасная
                </Badge>
              )}
              {a.ended_at && (
                <Badge size="xs" color="gray" variant="light">
                  в прошлом
                </Badge>
              )}
            </Group>
            <Text size="xs" c="dimmed">
              {a.organ.name} · {formatPeriod(a.started_at, a.ended_at)}
            </Text>
          </div>
        ))}
      </Stack>
    </Section>
  );
}

export function AuthoritiesSection({ profile }: { profile: OfficialProfile }) {
  const positionTitle = (positionId: string) =>
    profile.appointments.find((a) => a.position_id === positionId)?.position.title ?? '';
  return (
    <Section title="Полномочия">
      {profile.authorities.length === 0 && <Empty />}
      <Stack gap="xs">
        {profile.authorities.map((a) => (
          <Group key={a.id} gap="xs" align="flex-start" wrap="nowrap">
            <Badge variant="light" miw={110}>
              {AUTHORITY_LABELS[a.kind]}
            </Badge>
            <Text size="xs">
              {[
                a.scope.okpd2?.length ? `ОКПД2: ${a.scope.okpd2.join(', ')}` : null,
                a.scope.okved?.length ? `ОКВЭД: ${a.scope.okved.join(', ')}` : null,
                a.scope.territory,
              ]
                .filter(Boolean)
                .join(' · ')}
              <Text span size="xs" c="dimmed">
                {' '}
                ({positionTitle(a.position_id).toLowerCase()})
              </Text>
            </Text>
          </Group>
        ))}
      </Stack>
    </Section>
  );
}

export function RelativesSection({ profile }: { profile: OfficialProfile }) {
  return (
    <Section title="Родственники">
      {profile.relatives.length === 0 && <Empty />}
      <Stack gap="xs">
        {profile.relatives.map((r) => (
          <div key={r.kinship_id}>
            <Text size="sm">
              <b>{r.person.full_name}</b> — {KINSHIP_LABELS[r.kind]}
            </Text>
            <Text size="xs" c="dimmed">
              {[
                r.person.birth_date && `д.р. ${formatDate(r.person.birth_date)}`,
                r.person.inn && `ИНН ${r.person.inn}`,
                r.person.address,
              ]
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </div>
        ))}
      </Stack>
    </Section>
  );
}

export function CompaniesSection({ profile }: { profile: OfficialProfile }) {
  return (
    <Section title="Связанные компании">
      {profile.companies.length === 0 ? (
        <Empty />
      ) : (
        <Table.ScrollContainer minWidth={560}>
          <Table highlightOnHover={false}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Компания</Table.Th>
                <Table.Th>Связь</Table.Th>
                <Table.Th>Контракты</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {profile.companies.map((c) => (
                <Table.Tr key={`${c.company.id}-${c.via_person_id}-${c.role}`}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {c.company.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      ИНН {c.company.inn} · ОКВЭД {c.company.okved}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {COMPANY_ROLE_LABELS[c.role]}
                      {c.share ? ` ${c.share}%` : ''}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {c.relation === 'self'
                        ? 'сам служащий'
                        : `${KINSHIP_LABELS[c.relation]}: ${c.via_person_name}`}
                      {' · '}
                      {formatPeriod(c.started_at, c.ended_at)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{c.contracts_count}</Text>
                    {c.contracts_amount > 0 && (
                      <Text size="xs" c="dimmed">
                        {formatMoneyShort(c.contracts_amount)}
                      </Text>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Section>
  );
}
