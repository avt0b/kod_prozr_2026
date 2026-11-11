import { Button, CopyButton, Group, Paper, Text } from '@mantine/core';
import { IconCheck, IconCopy } from '@tabler/icons-react';
import type { ReportDraft } from '@/shared/api';
import { formatDateTime } from '@/shared/lib/format';

export function ReportView({ report }: { report: ReportDraft }) {
  return (
    <Paper p="xl" radius="md">
      <Group justify="space-between" mb="md">
        <Text size="sm" c="dimmed">
          Черновик от {formatDateTime(report.created_at)}
        </Text>
        <CopyButton value={report.text} timeout={2000}>
          {({ copied, copy }) => (
            <Button
              variant={copied ? 'filled' : 'light'}
              color={copied ? 'teal' : undefined}
              leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
              onClick={copy}
            >
              {copied ? 'Скопировано' : 'Копировать текст'}
            </Button>
          )}
        </CopyButton>
      </Group>
      <Text
        component="pre"
        ff="monospace"
        size="sm"
        style={{ whiteSpace: 'pre-wrap', margin: 0, lineHeight: 1.6 }}
      >
        {report.text}
      </Text>
    </Paper>
  );
}
