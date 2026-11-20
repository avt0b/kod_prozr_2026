import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';
import { answerGazePoint, draftGazePoint } from './mascotText';
import './alexey.css';

type Gaze =
  | { kind: 'idle' | 'waiting' }
  | { kind: 'typing'; field: RefObject<HTMLTextAreaElement>; caret: number }
  | { kind: 'speaking'; answer: RefObject<HTMLSpanElement>; glyph: string };

type Point = { x: number; y: number };

const ART_SIZE = 120;

function mouth(gaze: Gaze, reducedMotion: boolean) {
  if (gaze.kind !== 'speaking' || reducedMotion || !gaze.glyph) return [40, 3.5];
  if (/^[оеёую]$/i.test(gaze.glyph)) return [15, 13];
  if (/^[аыяиэ]$/i.test(gaze.glyph)) return [24, 11];
  if (/^[бмп\s,.!?—]$/i.test(gaze.glyph)) return [30, 4];
  return [21, 8];
}

export function AlexeyMascot({
  seat,
  gaze,
  reducedMotion,
}: {
  seat: HTMLElement | null;
  gaze: Gaze;
  reducedMotion: boolean;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const artwork = useRef<SVGSVGElement>(null);
  const eyes = useRef<SVGGElement>(null);
  const mirror = useRef<HTMLDivElement>(null);
  const placed = useRef(false);
  const gazeRef = useRef(gaze);
  const requestGaze = useRef<() => void>();
  const pointer = useRef<Point>();

  useLayoutEffect(() => {
    const element = holder.current;
    const stage = element?.parentElement;
    if (!element || !stage || !seat) return;
    const place = () => {
      const from = stage.getBoundingClientRect();
      const to = seat.getBoundingClientRect();
      if (!to.width || !from.width) return;
      // Convert viewport positions into the stage's coordinates during page entrance.
      const ratio = from.width / stage.offsetWidth;
      element.style.transform = `translate(${(to.left - from.left) / ratio}px, ${(to.top - from.top) / ratio}px) scale(${to.width / ratio / ART_SIZE})`;
      requestGaze.current?.();
    };
    place();
    if (!placed.current) {
      placed.current = true;
      // The first placement has no flight path; later seat changes animate.
      void element.offsetWidth;
      element.dataset.placed = 'true';
    }
    const observer = new ResizeObserver(place);
    observer.observe(stage);
    observer.observe(seat);
    return () => observer.disconnect();
  }, [seat]);

  useLayoutEffect(() => {
    gazeRef.current = gaze;
    requestGaze.current?.();
  }, [gaze]);

  useEffect(() => {
    if (reducedMotion) {
      eyes.current?.style.removeProperty('transform');
      return;
    }
    const element = holder.current;
    let frame = 0;
    function update() {
      frame = 0;
      if (!eyes.current || !artwork.current) return;
      const source = gazeRef.current;
      let target: Point | undefined;
      if (source.kind === 'idle') target = pointer.current;
      if (source.kind === 'typing' && source.field.current && mirror.current) {
        target = draftGazePoint(source.field.current, mirror.current, source.caret);
      }
      if (source.kind === 'speaking' && source.answer.current) {
        target = answerGazePoint(source.answer.current);
      }
      const matrix = artwork.current.getScreenCTM();
      const point =
        target && matrix
          ? new DOMPoint(target.x, target.y).matrixTransform(matrix.inverse())
          : undefined;
      const x = point ? point.x - 100 : 0;
      const y = point ? point.y - 112 : 0;
      const length = Math.hypot(x, y, 128);
      eyes.current.style.transform = `translate(${(x / length) * 9}px, ${(y / length) * 7}px)`;
    }
    function schedule() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    function move(event: PointerEvent) {
      if (event.pointerType !== 'mouse') return;
      pointer.current = { x: event.clientX, y: event.clientY };
      if (gazeRef.current.kind === 'idle') schedule();
    }
    function leave() {
      pointer.current = undefined;
      if (gazeRef.current.kind === 'idle') schedule();
    }
    requestGaze.current = schedule;
    schedule();
    window.addEventListener('pointermove', move, { passive: true });
    document.documentElement.addEventListener('pointerleave', leave);
    window.addEventListener('blur', leave);
    window.addEventListener('scroll', schedule, { capture: true, passive: true });
    window.addEventListener('resize', schedule);
    element?.addEventListener('transitionend', schedule);

    return () => {
      requestGaze.current = undefined;
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', move);
      document.documentElement.removeEventListener('pointerleave', leave);
      window.removeEventListener('blur', leave);
      window.removeEventListener('scroll', schedule, true);
      window.removeEventListener('resize', schedule);
      element?.removeEventListener('transitionend', schedule);
    };
  }, [reducedMotion]);

  const [width, height] = mouth(gaze, reducedMotion);
  return (
    <>
      <div className="assistant-alexey" ref={holder} data-state={gaze.kind} aria-hidden="true">
        <svg
          ref={artwork}
          className="assistant-alexey-art"
          viewBox="0 0 200 200"
          width={ART_SIZE}
          height={ART_SIZE}
        >
          <g data-part="coat">
            <path
              fill="#101b29"
              d="M10 194 Q15 184 25 178 L68 159 L129 158 L174 178 Q184 182 190 194 Z"
            />
            <path fill="#cc1728" d="M16 190 L25 182 L54 170 L72 190 Z" />
            <path fill="#cc1728" d="M128 190 L146 170 L175 182 L184 190 Z" />
            <path fill="#a7d7ee" d="M69 172 H96 L90 192 Z" />
            <path fill="#a7d7ee" d="M104 172 H130 L110 192 Z" />
            <polygon
              fill="#b2dff5"
              points="37.000,177.400 38.514,180.916 42.326,181.270 39.450,183.796 40.292,187.530 37.000,185.576 33.708,187.530 34.550,183.796 31.674,181.270 35.486,180.916"
            />
            <polygon
              fill="#b2dff5"
              points="51.000,177.400 52.514,180.916 56.326,181.270 53.450,183.796 54.292,187.530 51.000,185.576 47.708,187.530 48.550,183.796 45.674,181.270 49.486,180.916"
            />
            <polygon
              fill="#b2dff5"
              points="148.000,177.400 149.514,180.916 153.326,181.270 150.450,183.796 151.292,187.530 148.000,185.576 144.708,187.530 145.550,183.796 142.674,181.270 146.486,180.916"
            />
            <polygon
              fill="#b2dff5"
              points="162.000,177.400 163.514,180.916 167.326,181.270 164.450,183.796 165.292,187.530 162.000,185.576 158.708,187.530 159.550,183.796 156.674,181.270 160.486,180.916"
            />
          </g>
          <g data-part="head">
            <path
              fill="#101b29"
              d="M44 96 H156 Q171 96 171 112 V118 Q171 132 157 132 H43 Q29 132 29 118 V112 Q29 96 44 96 Z"
            />
            <path
              fill="#a7d7ee"
              d="M45 102 H155 Q165 102 165 112 V118 Q165 126 155 126 H45 Q35 126 35 118 V111 Q35 102 45 102 Z"
            />
            <path
              fill="#101b29"
              d="M40 76 Q42 69 54 69 H145 Q156 69 157 80 V145 Q157 170 132 172 H67 Q40 171 40 146 Z"
            />
            <path
              fill="#a7d7ee"
              d="M46 94 Q46 84 51 77 H148 Q151 85 151 96 V147 Q151 165 132 166 H67 Q46 165 46 147 Z"
            />
            <path fill="#101b29" d="M61 96 H92 V102 H61 Z" />
            <path fill="#101b29" d="M107 96 L136 91 L137 97 L108 102 Z" />
            <path fill="#101b29" d="M100 119 L107 132 H93 Z" />
            <g className="assistant-alexey-pupils" ref={eyes}>
              <g className="assistant-alexey-blink" fill="#101b29">
                <circle cx="77.5" cy="112" r="5.7" />
                <circle cx="121.5" cy="112" r="5.7" />
              </g>
            </g>
            <rect
              className="assistant-alexey-mouth"
              x={100 - width / 2}
              y={147 - height / 2}
              width={width}
              height={height}
              rx={height / 2}
              fill="#101b29"
            />
          </g>
          <g data-part="cap">
            <path
              fill="#101b29"
              d="M32 66 C15 58 17 44 32 31 C48 16 74 7 100 7 C126 7 152 16 168 31 C184 45 185 59 167 67 C153 73 128 77 100 77 C71 77 47 74 32 66 Z"
            />
            <path
              fill="#b2dff5"
              d="M28 39 C45 22 71 13 100 13 C129 13 154 22 172 39 V41 C154 25 129 17 100 17 C71 17 47 25 28 41 Z"
            />
            <path
              fill="#cc1728"
              d="M41 56 Q67 39 100 39 Q133 39 157 56 V71 Q132 64 100 64 Q66 64 41 71 Z"
            />
            <path
              fill="#101b29"
              d="M37 70 Q63 61 100 61 Q137 61 163 70 Q167 74 162 80 Q143 86 100 86 Q57 86 38 80 Q32 76 37 70 Z"
            />
            <path
              strokeWidth="3.2"
              strokeLinecap="round"
              stroke="#b2dff5"
              fill="none"
              d="M43 74 Q100 59 154 74"
            />
            <polygon
              fill="#b2dff5"
              points="100.000,42.400 102.596,48.427 109.130,49.033 104.200,53.365 105.643,59.767 100.000,56.416 94.357,59.767 95.800,53.365 90.870,49.033 97.404,48.427"
            />
          </g>
        </svg>
      </div>
      <div ref={mirror} className="assistant-alexey-mirror" aria-hidden="true" />
    </>
  );
}
