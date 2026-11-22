import { useEffect, useRef, useState } from 'react';
import { splitGraphemes } from './mascotText';

export function useAnswerReveal(reducedMotion: boolean) {
  const [playback, setPlayback] = useState<{ id: number; text: string; glyph: string }>();
  const frame = useRef(0);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);
  useEffect(() => {
    if (!reducedMotion) return;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setPlayback(undefined));
  }, [reducedMotion]);

  function reveal(id: number, text: string) {
    cancelAnimationFrame(frame.current);
    if (reducedMotion || !text) {
      setPlayback(undefined);
      return;
    }
    const glyphs = splitGraphemes(text);
    const duration = Math.min(3400, Math.max(420, glyphs.length * 24));
    const start = performance.now();
    let visible = 0;
    setPlayback({ id, text: '', glyph: '' });

    function advance(now: number) {
      const count = Math.min(
        glyphs.length,
        Math.floor(((now - start) / duration) * glyphs.length) + 1,
      );
      if (count >= glyphs.length) {
        setPlayback(undefined);
        return;
      }
      if (count !== visible) {
        visible = count;
        setPlayback({ id, text: glyphs.slice(0, count).join(''), glyph: glyphs[count - 1] });
      }
      frame.current = requestAnimationFrame(advance);
    }

    frame.current = requestAnimationFrame(advance);
  }

  return { playback: reducedMotion ? undefined : playback, reveal };
}
