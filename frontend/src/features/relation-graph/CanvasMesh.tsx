import { useEffect, useRef } from 'react';
import { useMediaQuery, useReducedMotion } from '@mantine/hooks';

/** The memoized mesh follows the pointer; it redraws only while the effect is settling. */
export function CanvasMesh() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reducedMotion = useReducedMotion();
  const finePointer = useMediaQuery('(hover: hover) and (pointer: fine)');

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || reducedMotion || !finePointer) return;

    const radius = 230;
    const spacing = 26;
    const cursor = { x: 0, y: 0, depth: 0 };
    const target = { x: 0, y: 0, depth: 0 };
    const dark = () => document.documentElement.dataset.mantineColorScheme === 'dark';
    let frame = 0;
    let width = 0;
    let height = 0;

    function requestDraw() {
      if (!frame) frame = requestAnimationFrame(draw);
    }

    function draw() {
      frame = 0;
      if (!ctx || !canvas) return;
      cursor.x += (target.x - cursor.x) * 0.14;
      cursor.y += (target.y - cursor.y) * 0.14;
      cursor.depth += (target.depth - cursor.depth) * 0.1;
      ctx.clearRect(0, 0, width, height);

      if (
        Math.abs(target.depth - cursor.depth) > 0.002 ||
        (cursor.depth > 0.01 && Math.hypot(target.x - cursor.x, target.y - cursor.y) > 0.5)
      ) {
        requestDraw();
      }
      canvas.toggleAttribute('data-active', cursor.depth > 0.012);
      if (cursor.depth <= 0.012) return;

      const tint = dark() ? '162, 193, 228' : '15, 23, 42';
      const lens = ctx.createRadialGradient(
        cursor.x,
        cursor.y,
        4,
        cursor.x,
        cursor.y,
        radius * 1.3,
      );
      lens.addColorStop(0, `rgba(${tint}, ${0.095 * cursor.depth})`);
      lens.addColorStop(0.45, `rgba(${tint}, ${0.045 * cursor.depth})`);
      lens.addColorStop(1, `rgba(${tint}, 0)`);
      ctx.fillStyle = lens;
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = dark() ? '#a3aec239' : '#1d1d1f27';
      ctx.beginPath();

      for (let y = 0; y < height; y += spacing) {
        for (let x = 0; x < width; x += spacing) {
          const dx = x - cursor.x;
          const dy = y - cursor.y;
          const distance = Math.hypot(dx, dy);
          const pull =
            distance > 0 && distance < radius
              ? (17 * cursor.depth * Math.sin(((1 - distance / radius) * Math.PI) / 2)) / distance
              : 0;
          const px = x - dx * pull;
          const py = y - dy * pull;
          ctx.moveTo(px + 1, py);
          ctx.arc(px, py, 1, 0, Math.PI * 2);
        }
      }
      ctx.fill();
    }

    const observer = new ResizeObserver(() => {
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      requestDraw();
    });
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return;
      const bounds = canvas.getBoundingClientRect();
      const x = event.clientX - bounds.left;
      const y = event.clientY - bounds.top;
      if (!target.depth) {
        cursor.x = x;
        cursor.y = y;
      }
      target.x = x;
      target.y = y;
      target.depth = 1;
      requestDraw();
    };
    const leave = () => {
      target.depth = 0;
      requestDraw();
    };
    observer.observe(canvas);
    window.addEventListener('pointermove', move, { passive: true });
    document.documentElement.addEventListener('pointerleave', leave);
    window.addEventListener('blur', leave);

    return () => {
      observer.disconnect();
      window.removeEventListener('pointermove', move);
      document.documentElement.removeEventListener('pointerleave', leave);
      window.removeEventListener('blur', leave);
      cancelAnimationFrame(frame);
      canvas.removeAttribute('data-active');
    };
  }, [finePointer, reducedMotion]);

  return <canvas ref={canvasRef} className="profile-mesh" aria-hidden="true" />;
}
