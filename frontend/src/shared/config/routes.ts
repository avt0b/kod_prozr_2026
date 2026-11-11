/** Пути приложения. Ссылки строим только через эти функции, не хардкодим строки в компонентах. */
export const routes = {
  overview: () => '/',
  officials: () => '/officials',
  official: (id: string) => `/officials/${id}`,
  appeals: () => '/appeals',
  appealNew: () => '/appeals/new',
  appeal: (id: string) => `/appeals/${id}`,
  report: (id: string) => `/reports/${id}`,
  assistant: () => '/assistant',
} as const;
