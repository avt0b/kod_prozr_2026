import { useEffect, useId, useRef, type PointerEvent } from 'react';

function createEdgeMap(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  radius: number,
) {
  context.canvas.width = width;
  context.canvas.height = height;
  const map = context.createImageData(width, height);
  const bevel = Math.min(15, radius * 0.55);
  const innerX = width / 2 - radius;
  const innerY = height / 2 - radius;

  // Displace the backdrop along the normal of the rounded edge. The center stays flat.
  for (let y = 0, offset = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1, offset += 4) {
      const cx = x + 0.5 - width / 2;
      const cy = y + 0.5 - height / 2;
      const dx = Math.abs(cx) - innerX;
      const dy = Math.abs(cy) - innerY;
      const edgeX = Math.max(0, dx);
      const edgeY = Math.max(0, dy);
      const distance = Math.hypot(edgeX, edgeY);
      const depth = radius - distance - Math.min(0, Math.max(dx, dy));
      const strength = Math.max(0, 1 - Math.abs(depth - 2) / bevel) ** 1.65;
      const shift = distance ? (126 * strength) / distance : 0;
      map.data[offset] = 128 - Math.sign(cx) * edgeX * shift;
      map.data[offset + 1] = 128 - Math.sign(cy) * edgeY * shift;
      map.data[offset + 3] = 255;
    }
  }

  context.putImageData(map, 0, 0);
  return context.canvas.toDataURL('image/png');
}

export function useLiquidGlass<Element extends HTMLElement>() {
  const id = useId();
  const ref = useRef<Element>(null);
  const filterRef = useRef<SVGFilterElement>(null);
  const imageRef = useRef<SVGFEImageElement>(null);

  useEffect(() => {
    const surface = ref.current;
    const filter = filterRef.current;
    const image = imageRef.current;
    if (
      !surface ||
      !filter ||
      !image ||
      !CSS.supports('backdrop-filter', 'url("#lens") blur(2px)')
    ) {
      return;
    }
    const context = document.createElement('canvas').getContext('2d');
    if (!context) return;
    const observer = new ResizeObserver(() => {
      const { clientWidth: width, clientHeight: height } = surface;
      if (!width || !height) return;
      const radius = Math.min(
        parseFloat(getComputedStyle(surface).borderTopLeftRadius),
        width / 2,
        height / 2,
      );
      if (radius <= 0) return;
      filter.setAttribute('width', String(width + 40));
      filter.setAttribute('height', String(height + 40));
      image.setAttribute('width', String(width));
      image.setAttribute('height', String(height));
      image.setAttribute('href', createEdgeMap(context, width, height, radius));
      surface.style.setProperty('--glass-lens-filter', `url("#${id}")`);
      surface.dataset.refracting = '';
    });
    observer.observe(surface);
    return () => observer.disconnect();
  }, [id]);

  const light = (event: PointerEvent<Element>) => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const surface = event.currentTarget;
    const bounds = surface.getBoundingClientRect();
    surface.style.setProperty('--glass-light-x', `${event.clientX - bounds.left}px`);
    surface.style.setProperty('--glass-light-y', `${event.clientY - bounds.top}px`);
    surface.dataset.lit = '';
  };
  const clear = (event: PointerEvent<Element>) => {
    delete event.currentTarget.dataset.lit;
  };

  return {
    props: {
      ref,
      onPointerMove: light,
      onPointerDown: light,
      onPointerLeave: clear,
      onPointerCancel: clear,
      onPointerUp: (event: PointerEvent<Element>) => {
        if (event.pointerType === 'touch') clear(event);
      },
    },
    lens: (
      <svg aria-hidden="true" width="0" height="0" style={{ position: 'absolute' }}>
        <filter
          ref={filterRef}
          id={id}
          x="-20"
          y="-20"
          filterUnits="userSpaceOnUse"
          primitiveUnits="userSpaceOnUse"
          colorInterpolationFilters="sRGB"
        >
          <feImage ref={imageRef} x="0" y="0" preserveAspectRatio="none" result="edge" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="edge"
            scale={24}
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </svg>
    ),
  };
}
