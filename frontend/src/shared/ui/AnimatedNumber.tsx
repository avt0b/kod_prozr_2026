import { useEffect, useRef } from 'react';

/** Animate only the visible number; assistive technology always receives the final value. */
export function AnimatedNumber({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    let from = previous.current;
    let frame = 0;
    const finish = () => {
      cancelAnimationFrame(frame);
      element.textContent = value.toLocaleString('ru-RU');
      previous.current = value;
    };
    const onVisibility = () => {
      if (document.hidden) finish();
    };
    const onPreference = () => {
      if (motion.matches) finish();
    };
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        element.closest('.stat-panel')?.setAttribute('data-motion-visible', '');
        if (motion.matches || document.hidden || from === value) {
          finish();
          return;
        }
        const started = performance.now();
        const tick = (now: number) => {
          const progress = Math.min(1, (now - started) / 1100);
          const next = Math.round(from + (value - from) * (1 - (1 - progress) ** 4));
          element.textContent = next.toLocaleString('ru-RU');
          previous.current = next;
          if (progress < 1) frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
      },
      { threshold: 0.35 },
    );
    observer.observe(element);
    const replay = () => {
      cancelAnimationFrame(frame);
      from = 0;
      observer.observe(element);
    };
    document.addEventListener('workspace:replay-motion', replay);
    motion.addEventListener('change', onPreference);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      motion.removeEventListener('change', onPreference);
      document.removeEventListener('visibilitychange', onVisibility);
      document.removeEventListener('workspace:replay-motion', replay);
    };
  }, [value]);
  return (
    <span className="animated-number">
      <span className="motion-sr-only">{value.toLocaleString('ru-RU')}</span>
      <span ref={ref} aria-hidden="true">
        {value.toLocaleString('ru-RU')}
      </span>
    </span>
  );
}
