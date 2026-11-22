import { useEffect } from 'react';

/** Заголовок вкладки на время жизни страницы; при уходе возвращается прежний. */
export function usePageTitle(title: string) {
  useEffect(() => {
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);
}
