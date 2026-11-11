import { Anchor, Group, Skeleton, Stack, Text } from '@mantine/core';
import { Link } from 'react-router';
import { useOfficial } from '@/features/officials/api';
import { routes } from '@/shared/config/routes';
import { RiskScoreBadge } from '@/shared/ui';

/** The appeal contract supplies IDs; profile data stays in the shared query cache. */
export function LinkedOfficialPreview({ id }: { id: string }) {
  const profile = useOfficial(id);
  const person = profile.data?.person;
  const appointment = profile.data?.appointments[0];
  return (
    <Group gap="xs" wrap="nowrap" align="flex-start">
      {profile.data && <RiskScoreBadge score={profile.data.risk.score} />}
      <Stack gap={2}>
        <Anchor
          component={Link}
          to={routes.official(id)}
          size="sm"
          onClick={(e) => e.stopPropagation()}
        >
          {person?.full_name ?? 'Открыть профиль служащего'}
        </Anchor>
        {profile.isPending && <Skeleton height={12} width={120} />}
        {appointment && (
          <Text size="xs" c="dimmed">
            {appointment.position.title} · {appointment.organ.name}
          </Text>
        )}
        {profile.isError && (
          <Text size="xs" c="dimmed">
            Сведения временно недоступны
          </Text>
        )}
      </Stack>
    </Group>
  );
}
