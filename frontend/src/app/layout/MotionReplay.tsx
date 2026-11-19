import { ActionIcon, Tooltip } from '@mantine/core';
import { useReducedMotion } from '@mantine/hooks';
import { IconPlayerPlay } from '@tabler/icons-react';

export function MotionReplay() {
  const reducedMotion = useReducedMotion();
  return (
    <Tooltip
      label={reducedMotion ? 'Уменьшение движения включено в системе' : 'Повторить анимации'}
    >
      <ActionIcon
        variant="default"
        size="lg"
        visibleFrom="sm"
        aria-label="Повторить анимации"
        disabled={reducedMotion}
        onClick={() => {
          const page = document.querySelector<HTMLElement>('.workspace-page');
          if (!page) return;
          page.setAttribute('data-motion-reset', '');
          // Commit one style reset to replay CSS without remounting screens or losing user input.
          void page.offsetWidth;
          page.removeAttribute('data-motion-reset');
          document.dispatchEvent(new Event('workspace:replay-motion'));
        }}
      >
        <IconPlayerPlay size={18} />
      </ActionIcon>
    </Tooltip>
  );
}
