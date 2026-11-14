import { Anchor, Stack, Table, Text } from '@mantine/core';
import { Link, useNavigate } from 'react-router';
import type { Appeal } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime, formatPercent } from '@/shared/lib/format';
import { LinkedOfficialPreview } from './LinkedOfficialPreview';
import { APPEAL_CHANNEL_LABELS } from '@/shared/lib/labels';
import { AppealCategoryBadge, AppealStatusBadge } from './AppealBadges';

export function AppealsTable({ items }: { items: Appeal[] }) {
  const navigate = useNavigate();
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={150}>Поступило</Table.Th>
            <Table.Th w={140}>Статус</Table.Th>
            <Table.Th w={190}>Категория</Table.Th>
            <Table.Th>Текст</Table.Th>
            <Table.Th>Уверенность</Table.Th>
            <Table.Th>Связанные служащие</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((a) => (
            <Table.Tr
              key={a.id}
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(routes.appeal(a.id))}
            >
              <Table.Td>
                <Text size="sm">{formatDateTime(a.received_at)}</Text>
                <Text size="xs" c="dimmed">
                  {APPEAL_CHANNEL_LABELS[a.channel]}
                </Text>
              </Table.Td>
              <Table.Td>
                <AppealStatusBadge status={a.status} />
              </Table.Td>
              <Table.Td>
                <AppealCategoryBadge category={a.analysis?.category} />
              </Table.Td>
              <Table.Td>
                <Text size="sm" lineClamp={2}>
                  <Anchor component={Link} to={routes.appeal(a.id)} size="sm">
                    {a.text}
                  </Anchor>
                </Text>
              </Table.Td>
              <Table.Td>{a.analysis ? formatPercent(a.analysis.confidence) : '—'}</Table.Td>
              <Table.Td>
                <Stack gap="xs">
                  {a.linked_person_ids.map((id) => (
                    <LinkedOfficialPreview key={id} id={id} />
                  ))}
                  {a.linked_person_ids.length === 0 && '—'}
                </Stack>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
