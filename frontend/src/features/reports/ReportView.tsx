import { Button, CopyButton, Group, Paper, Text } from '@mantine/core';
import { IconCheck, IconCopy, IconPrinter } from '@tabler/icons-react';
import type { ReportDraft } from '@/shared/api';

export function ReportActions({ text }: { text: string }) {
  return (
    <Group gap="xs">
      <CopyButton value={text} timeout={2000}>
        {({ copied, copy }) => (
          <Button
            variant="default"
            color={copied ? 'teal' : undefined}
            leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
            onClick={copy}
          >
            {copied ? 'Скопировано' : 'Копировать текст'}
          </Button>
        )}
      </CopyButton>
      <Button leftSection={<IconPrinter size={16} />} onClick={() => window.print()}>
        Печать
      </Button>
    </Group>
  );
}

export function ReportView({ report }: { report: ReportDraft }) {
  return (
    <Paper
      p={{ base: 'lg', sm: 48 }}
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
  );
}
