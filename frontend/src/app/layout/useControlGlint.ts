import { useEffect } from 'react';

/** One pointer listener covers shared buttons and popovers, including those rendered in portals. */
export function useControlGlint() {
  useEffect(() => {
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    let active: HTMLElement | null = null;

    function clear() {
      active?.removeAttribute('data-lit');
      active = null;
    }

    function illuminate(event: PointerEvent) {
      const target = event.target;
      const control =
        target instanceof Element ? target.closest<HTMLElement>('.workspace-control') : null;
      if (!control || control.matches(':disabled, [data-disabled], [aria-disabled="true"]')) {
        clear();
        return;
      }
      if (motion.matches || (event.pointerType === 'touch' && event.type === 'pointermove')) return;
      if (active !== control) clear();
      active = control;
      const bounds = control.getBoundingClientRect();
      control.style.setProperty('--glass-light-x', `${event.clientX - bounds.left}px`);
      control.style.setProperty('--glass-light-y', `${event.clientY - bounds.top}px`);
      control.dataset.lit = '';
    }

    function leave(event: PointerEvent) {
      if (event.relatedTarget instanceof Node && active?.contains(event.relatedTarget)) return;
      clear();
    }

    document.addEventListener('pointermove', illuminate, { passive: true });
    document.addEventListener('pointerdown', illuminate, { passive: true });
    document.addEventListener('pointerout', leave);
    document.addEventListener('pointercancel', clear);
    motion.addEventListener('change', clear);
    return () => {
      clear();
      document.removeEventListener('pointermove', illuminate);
      document.removeEventListener('pointerdown', illuminate);
      document.removeEventListener('pointerout', leave);
      document.removeEventListener('pointercancel', clear);
      motion.removeEventListener('change', clear);
    };
  }, []);
}
