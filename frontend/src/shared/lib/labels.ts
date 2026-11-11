/** Русские подписи для enum-значений контракта. Единственное место, где они живут. */
import type {
  AppealCategory,
  AppealChannel,
  AppealStatus,
  AuthorityKind,
  CompanyRoleKind,
  EntityType,
  GraphNodeType,
  KinshipKind,
  ProcurementMethod,
  RuleCode,
  Severity,
} from '@/shared/api/types';

export const RULE_TITLES: Record<RuleCode, string> = {
  R01: 'Родственник — поставщик органа',
  R02: 'Собственный бизнес',
  R03: 'Бывший работодатель — подрядчик',
  R04: '«Вращающаяся дверь»',
  R05: 'Общие контакты с подрядчиком',
  R06: 'Концентрация поставщика',
  R07: 'Упоминания в обращениях',
  R08: 'Аномалия относительно коллег',
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  high: 'высокий',
  medium: 'средний',
  low: 'низкий',
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  high: 'red',
  medium: 'orange',
  low: 'yellow',
};

export const SEVERITY_ORDER: Record<Severity, number> = { high: 3, medium: 2, low: 1 };

export const APPEAL_STATUS_LABELS: Record<AppealStatus, string> = {
  new: 'Новое',
  analyzed: 'Проанализировано',
  routed: 'Направлено',
  closed: 'Закрыто',
};

export const APPEAL_STATUS_COLORS: Record<AppealStatus, string> = {
  new: 'blue',
  analyzed: 'violet',
  routed: 'teal',
  closed: 'gray',
};

export const APPEAL_CATEGORY_LABELS: Record<AppealCategory, string> = {
  bribe: 'Взятка',
  conflict_of_interest: 'Конфликт интересов',
  procurement: 'Закупки',
  abuse_of_power: 'Превышение полномочий',
  other: 'Иное',
};

export const APPEAL_CHANNEL_LABELS: Record<AppealChannel, string> = {
  web: 'Интернет-приёмная',
  email: 'Электронная почта',
  hotline: 'Телефон доверия',
  letter: 'Письмо',
  personal: 'Личный приём',
};

export const AUTHORITY_LABELS: Record<AuthorityKind, string> = {
  procurement: 'Закупки',
  permits: 'Разрешения',
  inspection: 'Контроль и проверки',
  budget: 'Бюджет',
  hr: 'Кадры',
};

export const KINSHIP_LABELS: Record<KinshipKind, string> = {
  spouse: 'супруг(а)',
  child: 'ребёнок',
  parent: 'родитель',
  sibling: 'брат/сестра',
  in_law: 'свойственник',
  other: 'иное родство',
};

export const COMPANY_ROLE_LABELS: Record<CompanyRoleKind | 'employee', string> = {
  founder: 'учредитель',
  director: 'руководитель',
  employee: 'работник',
};

export const PROCUREMENT_METHOD_LABELS: Record<ProcurementMethod, string> = {
  auction: 'электронный аукцион',
  tender: 'конкурс',
  quotation: 'запрос котировок',
  single_supplier: 'единственный поставщик',
};

export const ENTITY_LABELS: Record<EntityType, string> = {
  person: 'Лицо',
  organization: 'Организация',
  position: 'Должность',
  money: 'Сумма',
  date: 'Дата',
  address: 'Адрес',
};

export const ENTITY_COLORS: Record<EntityType, string> = {
  person: 'red',
  organization: 'blue',
  position: 'grape',
  money: 'green',
  date: 'cyan',
  address: 'orange',
};

export const NODE_TYPE_LABELS: Record<GraphNodeType, string> = {
  person: 'Лицо',
  company: 'Компания',
  organ: 'Орган',
  contract: 'Контракт',
  appeal: 'Обращение',
};
