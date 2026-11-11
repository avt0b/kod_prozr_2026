import { Button, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import { routes } from '@/shared/config/routes';

export function NotFoundPage() {
  return (
    <Stack align="center" py={80} gap="sm">
      <Title order={2}>Страница не найдена</Title>
      <Text c="dimmed">Проверьте адрес или вернитесь на главную.</Text>
      <Button component={Link} to={routes.overview()} variant="light">
        На обзор
      </Button>
    </Stack>
  );
}
