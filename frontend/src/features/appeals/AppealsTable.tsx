import { Table, Text } from '@mantine/core';
import { useNavigate } from 'react-router';
import type { Appeal } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
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
                  {a.text}
                </Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
