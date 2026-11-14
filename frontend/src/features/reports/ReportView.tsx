import { Button, CopyButton, Group, Paper, Text } from '@mantine/core';
import { IconCheck, IconCopy, IconPrinter } from '@tabler/icons-react';
import type { ReportDraft } from '@/shared/api';
import { formatDateTime } from '@/shared/lib/format';

export function ReportView({ report }: { report: ReportDraft }) {
  return (
    <Paper p="xl" radius="md">
      <Group justify="space-between" mb="md">
        <Text size="sm" c="dimmed">
          Черновик от {formatDateTime(report.created_at)}
        </Text>
        <Group gap="xs">
          <Button
            variant="default"
            leftSection={<IconPrinter size={16} />}
            onClick={() => window.print()}
          >
            Печать
          </Button>
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
      </Group>
      <Paper
        withBorder
        p={{ base: 'md', sm: 48 }}
        bg="white"
        c="dark.9"
        className="report-document"
        style={{ fontFamily: "'PT Serif', Georgia, 'Times New Roman', serif" }}
      >
        <Text
          component="div"
          size="md"
          style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontFamily: 'inherit' }}
        >
          {report.text}
        </Text>
      </Paper>
    </Paper>
  );
}
