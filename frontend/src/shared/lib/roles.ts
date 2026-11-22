/** Роли приложения (#70). Модуль без зависимостей: его импортируют и e2e-тесты. */
export type Role = 'citizen' | 'analyst' | 'admin';
export const STAFF_ROLES: readonly Role[] = ['analyst', 'admin'];
export const ROLE_LABELS: Record<Role, string> = {
  citizen: 'Гражданин',
  analyst: 'Аналитик',
  admin: 'Администратор',
};
/** Стартовая страница роли: гражданин — свой кабинет, сотрудники — рабочее место. */
export const homeOf = (role: Role) => (role === 'citizen' ? '/citizen' : '/');
