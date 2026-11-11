/**
 * Синтетические данные для моков. Все лица и организации вымышлены, регион условный («Энская область»).
 * Таблицы нормализованы так же, как доменная модель в docs/contracts.md;
 * производные ответы (профиль, граф, рейтинг) собираются в ./db.ts.
 *
 * Демо-сценарий: P1 Соколов А.В. — начальник отдела закупок Минстроя; супруга P21 — учредитель
 * ООО «ДорСтройРесурс»; у ООО 5 контрактов с этим же министерством → флаг R01, высокий риск.
 */
import type {
  Appeal,
  AppealAnalysis,
  AppealEntity,
  Appointment,
  Authority,
  Company,
  CompanyRole,
  Contract,
  Employment,
  EntityType,
  Kinship,
  Organ,
  Person,
  Position,
  RuleCode,
  Severity,
} from '../types';

/** Детерминированный UUID: kind — тип сущности, n — номер. */
export const uid = (kind: number, n: number) =>
  `${kind.toString(16).padStart(8, '0')}-0000-4000-8000-${n.toString(16).padStart(12, '0')}`;

const K = {
  organ: 1,
  person: 2,
  position: 3,
  appointment: 4,
  authority: 5,
  kinship: 6,
  company: 7,
  role: 8,
  employment: 9,
  contract: 10,
  flag: 11,
  appeal: 12,
  report: 13,
} as const;

export const O = (n: number) => uid(K.organ, n);
export const P = (n: number) => uid(K.person, n);
export const POS = (n: number) => uid(K.position, n);
export const C = (n: number) => uid(K.company, n);
export const CT = (n: number) => uid(K.contract, n);
export const A = (n: number) => uid(K.appeal, n);
export const FLAG = (n: number) => uid(K.flag, n);
export const REPORT = (n: number) => uid(K.report, n);

/* ---------------- Органы ---------------- */

export const organs: Organ[] = [
  {
    id: O(1),
    name: 'Министерство строительства и ЖКХ Энской области',
    inn: '3601012345',
    region: 'Энская область',
  },
  {
    id: O(2),
    name: 'Департамент здравоохранения Энской области',
    inn: '3601023456',
    region: 'Энская область',
  },
  { id: O(3), name: 'Администрация города Энска', inn: '3602034567', region: 'Энская область' },
  {
    id: O(4),
    name: 'Комитет по управлению имуществом Энской области',
    inn: '3601045678',
    region: 'Энская область',
  },
];

/* ---------------- Лица ---------------- */

const SOKOLOV_ADDRESS = 'г. Энск, ул. Садовая, д. 14, кв. 37';
const KOZLOV_PHONE = '+7 (4732) 55-18-90';
const MIKHAILOV_ADDRESS = 'г. Энск, пр-т Победы, д. 102, оф. 5';

export const persons: Person[] = [
  // Служащие
  {
    id: P(1),
    full_name: 'Соколов Андрей Викторович',
    inn: '360100112233',
    birth_date: '1978-04-12',
    address: SOKOLOV_ADDRESS,
    phone: '+7 (900) 123-45-67',
  },
  {
    id: P(2),
    full_name: 'Петрова Елена Сергеевна',
    inn: '360100223344',
    birth_date: '1975-09-03',
    address: 'г. Энск, ул. Пушкина, д. 8, кв. 12',
  },
  {
    id: P(3),
    full_name: 'Кузнецов Дмитрий Олегович',
    inn: '360100334455',
    birth_date: '1986-01-27',
    address: 'г. Энск, ул. Лесная, д. 3, кв. 81',
  },
  {
    id: P(4),
    full_name: 'Морозов Игорь Николаевич',
    inn: '360100445566',
    birth_date: '1969-11-15',
    address: 'г. Энск, ул. Заводская, д. 21',
  },
  {
    id: P(5),
    full_name: 'Волкова Ольга Петровна',
    inn: '360100556677',
    birth_date: '1983-06-30',
    address: 'г. Энск, ул. Мира, д. 44, кв. 9',
  },
  {
    id: P(6),
    full_name: 'Лебедев Сергей Александрович',
    inn: '360100667788',
    birth_date: '1972-02-08',
    address: 'г. Энск, ул. Кирова, д. 17, кв. 2',
  },
  {
    id: P(7),
    full_name: 'Новикова Анна Викторовна',
    inn: '360100778899',
    birth_date: '1980-12-19',
    address: 'г. Энск, ул. Гагарина, д. 5, кв. 64',
  },
  {
    id: P(8),
    full_name: 'Козлов Артём Игоревич',
    inn: '360100889900',
    birth_date: '1991-07-22',
    address: 'г. Энск, ул. Советская, д. 90, кв. 15',
    phone: KOZLOV_PHONE,
  },
  {
    id: P(9),
    full_name: 'Смирнова Татьяна Юрьевна',
    inn: '360100990011',
    birth_date: '1977-03-14',
    address: 'г. Энск, ул. Чехова, д. 2, кв. 7',
  },
  {
    id: P(10),
    full_name: 'Попов Валерий Геннадьевич',
    inn: '360101001122',
    birth_date: '1965-10-01',
    address: 'Энский р-н, пос. Сосновка, ул. Озёрная, д. 1',
  },
  {
    id: P(11),
    full_name: 'Васильева Наталья Андреевна',
    inn: '360101112233',
    birth_date: '1989-05-25',
    address: 'г. Энск, ул. Строителей, д. 11, кв. 33',
  },
  {
    id: P(12),
    full_name: 'Фёдоров Максим Романович',
    inn: '360101223344',
    birth_date: '1990-08-09',
    address: 'г. Энск, ул. Ленина, д. 60, кв. 101',
  },
  {
    id: P(13),
    full_name: 'Михайлова Ирина Константиновна',
    inn: '360101334455',
    birth_date: '1981-04-04',
    address: 'г. Энск, ул. Тургенева, д. 9, кв. 4',
  },
  {
    id: P(14),
    full_name: 'Николаев Павел Дмитриевич',
    inn: '360101445566',
    birth_date: '1993-02-17',
    address: 'г. Энск, ул. Новая, д. 27, кв. 50',
  },
  {
    id: P(15),
    full_name: 'Егорова Светлана Борисовна',
    inn: '360101556677',
    birth_date: '1970-09-28',
    address: 'г. Энск, ул. Набережная, д. 3, кв. 18',
  },
  // Родственники и представители компаний
  {
    id: P(21),
    full_name: 'Соколова Марина Олеговна',
    inn: '360102112233',
    birth_date: '1981-08-19',
    address: SOKOLOV_ADDRESS,
  },
  {
    id: P(22),
    full_name: 'Соколов Кирилл Андреевич',
    birth_date: '2004-03-02',
    address: SOKOLOV_ADDRESS,
  },
  {
    id: P(23),
    full_name: 'Петров Алексей Иванович',
    inn: '360102223344',
    birth_date: '1973-01-11',
  },
  {
    id: P(24),
    full_name: 'Козлова Дарья Сергеевна',
    inn: '360102334455',
    birth_date: '1993-10-05',
    phone: KOZLOV_PHONE,
  },
  {
    id: P(25),
    full_name: 'Михайлов Олег Константинович',
    inn: '360102445566',
    birth_date: '1978-12-30',
    address: MIKHAILOV_ADDRESS,
  },
  { id: P(26), full_name: 'Лебедева Ксения Олеговна', birth_date: '1976-06-16' },
  {
    id: P(30),
    full_name: 'Гришин Роман Евгеньевич',
    inn: '360103001122',
    birth_date: '1985-05-05',
  },
  {
    id: P(31),
    full_name: 'Тарасов Виктор Павлович',
    inn: '360103112233',
    birth_date: '1979-02-21',
  },
  {
    id: P(32),
    full_name: 'Белов Константин Игоревич',
    inn: '360103223344',
    birth_date: '1974-07-07',
  },
  { id: P(33), full_name: 'Орлова Вера Николаевна', inn: '360103334455', birth_date: '1968-11-23' },
];

/* ---------------- Должности ---------------- */

export const positions: Position[] = [
  {
    id: POS(1),
    organ_id: O(1),
    title: 'Начальник отдела',
    department: 'Отдел государственных закупок',
    is_corruption_risky: true,
  },
  {
    id: POS(2),
    organ_id: O(2),
    title: 'Заместитель руководителя департамента',
    department: 'Руководство',
    is_corruption_risky: true,
  },
  {
    id: POS(3),
    organ_id: O(3),
    title: 'Главный специалист',
    department: 'Отдел лицензирования и разрешительной деятельности',
    is_corruption_risky: true,
  },
  {
    id: POS(4),
    organ_id: O(3),
    title: 'Начальник отдела',
    department: 'Отдел муниципального контроля',
    is_corruption_risky: true,
  },
  {
    id: POS(5),
    organ_id: O(4),
    title: 'Консультант',
    department: 'Отдел арендных отношений',
    is_corruption_risky: true,
  },
  {
    id: POS(6),
    organ_id: O(3),
    title: 'Начальник управления',
    department: 'Управление капитального строительства',
    is_corruption_risky: true,
  },
  {
    id: POS(7),
    organ_id: O(2),
    title: 'Главный бухгалтер',
    department: 'Финансово-экономический отдел',
    is_corruption_risky: true,
  },
  {
    id: POS(8),
    organ_id: O(1),
    title: 'Ведущий специалист',
    department: 'Отдел государственных закупок',
    is_corruption_risky: true,
  },
  {
    id: POS(9),
    organ_id: O(3),
    title: 'Начальник отдела',
    department: 'Отдел кадров и муниципальной службы',
    is_corruption_risky: false,
  },
  {
    id: POS(10),
    organ_id: O(1),
    title: 'Заместитель министра',
    department: 'Руководство',
    is_corruption_risky: true,
  },
  {
    id: POS(11),
    organ_id: O(4),
    title: 'Ведущий специалист',
    department: 'Отдел приватизации',
    is_corruption_risky: true,
  },
  {
    id: POS(12),
    organ_id: O(3),
    title: 'Инспектор',
    department: 'Отдел муниципального контроля',
    is_corruption_risky: true,
  },
  {
    id: POS(13),
    organ_id: O(3),
    title: 'Начальник отдела',
    department: 'Отдел выдачи разрешений на строительство',
    is_corruption_risky: true,
  },
  {
    id: POS(14),
    organ_id: O(2),
    title: 'Главный специалист',
    department: 'Отдел закупок',
    is_corruption_risky: true,
  },
  {
    id: POS(15),
    organ_id: O(3),
    title: 'Начальник управления',
    department: 'Финансовое управление',
    is_corruption_risky: true,
  },
  {
    id: POS(16),
    organ_id: O(1),
    title: 'Главный специалист',
    department: 'Отдел государственных закупок',
    is_corruption_risky: true,
  },
];

/* ---------------- Замещение должностей ---------------- */

const appt = (
  n: number,
  person: number,
  pos: number,
  started_at: string,
  ended_at: string | null = null,
): Appointment => ({
  id: uid(K.appointment, n),
  person_id: P(person),
  position_id: POS(pos),
  started_at,
  ended_at,
});

export const appointments: Appointment[] = [
  appt(1, 1, 16, '2015-02-01', '2020-05-31'),
  appt(2, 1, 1, '2020-06-01'),
  appt(3, 2, 2, '2019-09-16'),
  appt(4, 3, 3, '2023-07-03'),
  appt(5, 4, 4, '2014-03-10', '2025-03-31'),
  appt(6, 5, 5, '2018-01-15'),
  appt(7, 6, 6, '2017-04-03'),
  appt(8, 7, 7, '2016-10-10'),
  appt(9, 8, 8, '2021-08-02'),
  appt(10, 9, 9, '2012-05-21'),
  appt(11, 10, 10, '2019-01-28'),
  appt(12, 11, 11, '2022-02-14'),
  appt(13, 12, 12, '2020-11-09'),
  appt(14, 13, 13, '2022-09-01'),
  appt(15, 14, 14, '2023-03-20'),
  appt(16, 15, 15, '2015-06-01'),
];

/* ---------------- Полномочия ---------------- */

let authN = 0;
const auth = (pos: number, kind: Authority['kind'], scope: Authority['scope']): Authority => ({
  id: uid(K.authority, ++authN),
  position_id: POS(pos),
  kind,
  scope,
});

export const authorities: Authority[] = [
  auth(1, 'procurement', { okpd2: ['41.20', '42.11', '43.99'], territory: 'Энская область' }),
  auth(16, 'procurement', { okpd2: ['41.20', '42.11'], territory: 'Энская область' }),
  auth(2, 'procurement', { okpd2: ['32.50', '21.20'], territory: 'Энская область' }),
  auth(2, 'budget', { territory: 'Энская область' }),
  auth(3, 'permits', { okved: ['47.73', '56.10'], territory: 'г. Энск' }),
  auth(4, 'inspection', { okved: ['35.30', '43.22'], territory: 'г. Энск' }),
  auth(5, 'permits', { territory: 'Энская область' }),
  auth(6, 'procurement', { okpd2: ['41.20', '42.11'], territory: 'г. Энск' }),
  auth(7, 'budget', { territory: 'Энская область' }),
  auth(8, 'procurement', { okpd2: ['41.20', '43.39'], territory: 'Энская область' }),
  auth(9, 'hr', { territory: 'г. Энск' }),
  auth(10, 'procurement', { okpd2: ['41.20', '42.11', '43.99'], territory: 'Энская область' }),
  auth(10, 'budget', { territory: 'Энская область' }),
  auth(11, 'permits', { territory: 'Энская область' }),
  auth(12, 'inspection', { okved: ['56.10', '47.11'], territory: 'г. Энск' }),
  auth(13, 'permits', { okved: ['41.20'], territory: 'г. Энск' }),
  auth(14, 'procurement', { okpd2: ['32.50', '21.20'], territory: 'Энская область' }),
  auth(15, 'budget', { territory: 'г. Энск' }),
];

/* ---------------- Родство ---------------- */

let kinN = 0;
const kin = (person: number, relative: number, kind: Kinship['kind']): Kinship => ({
  id: uid(K.kinship, ++kinN),
  person_id: P(person),
  relative_id: P(relative),
  kind,
});

export const kinships: Kinship[] = [
  kin(1, 21, 'spouse'),
  kin(1, 22, 'child'),
  kin(2, 23, 'spouse'),
  kin(8, 24, 'spouse'),
  kin(13, 25, 'sibling'),
  kin(6, 26, 'spouse'),
];

/* ---------------- Компании ---------------- */

export const companies: Company[] = [
  {
    id: C(1),
    inn: '3664251870',
    ogrn: '1213600012345',
    name: 'ООО «ДорСтройРесурс»',
    okved: '41.20',
    address: SOKOLOV_ADDRESS,
    phone: '+7 (4732) 20-11-37',
    registered_at: '2021-03-15',
    status: 'active',
  },
  {
    id: C(2),
    inn: '3664198234',
    ogrn: '1183600054321',
    name: 'ООО «МедТехСервис»',
    okved: '46.46',
    address: 'г. Энск, ул. Космонавтов, д. 15',
    phone: '+7 (4732) 31-40-02',
    registered_at: '2018-06-20',
    status: 'active',
  },
  {
    id: C(3),
    inn: '3663087123',
    ogrn: '1123600067890',
    name: 'ООО «ЭнскЛицензКонсалт»',
    okved: '69.10',
    address: 'г. Энск, ул. Плехановская, д. 33, оф. 210',
    phone: '+7 (4732) 44-90-15',
    registered_at: '2012-11-02',
    status: 'active',
  },
  {
    id: C(4),
    inn: '3662145678',
    ogrn: '1093600011223',
    name: 'ООО «ЭнскТеплоМонтаж»',
    okved: '43.22',
    address: 'г. Энск, ул. Труда, д. 7',
    phone: '+7 (4732) 61-22-80',
    registered_at: '2009-04-17',
    status: 'active',
  },
  {
    id: C(5),
    inn: '3665011987',
    ogrn: '1203600098765',
    name: 'ООО «Энск-Снаб»',
    okved: '46.73',
    address: 'г. Энск, ул. Депутатская, д. 4',
    phone: KOZLOV_PHONE,
    registered_at: '2020-10-08',
    status: 'active',
  },
  {
    id: C(6),
    inn: '3661098712',
    ogrn: '1073600076543',
    name: 'ООО «ДорСтройИнвест»',
    okved: '42.11',
    address: 'г. Энск, Московский пр-т, д. 120',
    phone: '+7 (4732) 70-70-70',
    registered_at: '2007-08-30',
    status: 'active',
  },
  {
    id: C(7),
    inn: '3663112244',
    ogrn: '1133600033445',
    name: 'ООО «ГрадПроект»',
    okved: '71.11',
    address: MIKHAILOV_ADDRESS,
    phone: '+7 (4732) 52-03-19',
    registered_at: '2013-02-12',
    status: 'active',
  },
  {
    id: C(8),
    inn: '3664207531',
    ogrn: '1193600087654',
    name: 'ООО «ФармаЛайн»',
    okved: '46.46',
    address: 'г. Энск, ул. Ворошилова, д. 2а',
    phone: '+7 (4732) 39-55-11',
    registered_at: '2019-12-03',
    status: 'active',
  },
];

/* ---------------- Роли в компаниях ---------------- */

let roleN = 0;
const role = (
  company: number,
  person: number,
  r: CompanyRole['role'],
  share: number | null,
  started_at: string,
): CompanyRole => ({
  id: uid(K.role, ++roleN),
  company_id: C(company),
  person_id: P(person),
  role: r,
  share,
  started_at,
  ended_at: null,
});

export const companyRoles: CompanyRole[] = [
  role(1, 21, 'founder', 100, '2021-03-15'),
  role(1, 30, 'director', null, '2021-03-15'),
  role(2, 2, 'founder', 50, '2018-06-20'),
  role(2, 23, 'founder', 50, '2018-06-20'),
  role(2, 23, 'director', null, '2018-06-20'),
  role(3, 32, 'founder', 100, '2012-11-02'),
  role(4, 33, 'founder', 100, '2009-04-17'),
  role(5, 31, 'founder', 100, '2020-10-08'),
  role(6, 32, 'director', null, '2015-01-12'),
  role(7, 25, 'director', null, '2016-05-10'),
  role(8, 31, 'director', null, '2019-12-03'),
];

/* ---------------- Трудоустройство вне госслужбы ---------------- */

let empN = 0;
const emp = (
  person: number,
  company: number,
  started_at: string,
  ended_at: string | null,
): Employment => ({
  id: uid(K.employment, ++empN),
  person_id: P(person),
  company_id: C(company),
  started_at,
  ended_at,
});

export const employments: Employment[] = [
  emp(3, 3, '2017-09-01', '2023-06-30'),
  emp(4, 4, '2025-04-15', null),
  emp(13, 7, '2014-03-01', '2022-08-26'),
];

/* ---------------- Контракты ---------------- */

const ct = (
  n: number,
  organ: number,
  company: number,
  amount: number,
  signed_at: string,
  okpd2: string,
  method: Contract['method'],
): Contract => ({
  id: CT(n),
  reg_number: `236010123452${signed_at.slice(2, 4)}${String(n).padStart(6, '0')}`,
  customer_organ_id: O(organ),
  supplier_company_id: C(company),
  amount,
  signed_at,
  okpd2,
  method,
});

export const contracts: Contract[] = [
  // Демо-сценарий: ООО «ДорСтройРесурс» ← Минстрой
  ct(1, 1, 1, 12_400_000, '2024-04-18', '41.20.40', 'quotation'),
  ct(2, 1, 1, 18_950_000, '2024-09-02', '42.11.10', 'auction'),
  ct(3, 1, 1, 7_350_000, '2025-02-11', '43.99.90', 'single_supplier'),
  ct(4, 1, 1, 26_100_000, '2025-06-27', '41.20.40', 'auction'),
  ct(5, 1, 1, 21_800_000, '2026-03-05', '42.11.10', 'auction'),
  // Бывший работодатель Кузнецова
  ct(6, 3, 3, 1_850_000, '2024-02-20', '69.10.19', 'quotation'),
  ct(7, 3, 3, 2_400_000, '2025-05-14', '69.10.19', 'quotation'),
  // Компания, куда перешёл Морозов
  ct(8, 3, 4, 9_700_000, '2025-08-01', '43.22.12', 'auction'),
  // Общий телефон с Козловым
  ct(9, 1, 5, 3_120_000, '2023-11-30', '46.73.16', 'quotation'),
  ct(10, 1, 5, 4_480_000, '2025-03-19', '46.73.16', 'auction'),
  // Концентрация поставщика в администрации
  ct(11, 3, 6, 54_300_000, '2024-05-06', '42.11.20', 'auction'),
  ct(12, 3, 6, 61_900_000, '2025-04-22', '42.11.20', 'auction'),
  ct(13, 3, 6, 38_750_000, '2026-04-10', '42.11.20', 'tender'),
  // Бывший работодатель Михайловой
  ct(14, 3, 7, 5_600_000, '2024-10-03', '71.12.13', 'tender'),
  // Поставки в здравоохранение
  ct(15, 2, 8, 14_200_000, '2025-01-28', '32.50.13', 'auction'),
  ct(16, 2, 8, 9_850_000, '2026-02-16', '21.20.10', 'auction'),
];

/* ---------------- Флаги риска ---------------- */

export interface FlagSeed {
  n: number;
  person: number;
  rule_code: RuleCode;
  severity: Severity;
  weight: number;
  explanation: string;
  evidence: string[];
}

export const LEGAL_REFS: Partial<Record<RuleCode, string>> = {
  R01: 'Федеральный закон от 25.12.2008 № 273-ФЗ «О противодействии коррупции», ст. 10, 11',
  R02: 'Федеральный закон от 27.07.2004 № 79-ФЗ «О государственной гражданской службе РФ», ст. 17',
  R03: 'Федеральный закон от 25.12.2008 № 273-ФЗ «О противодействии коррупции», ст. 10',
  R04: 'Федеральный закон от 25.12.2008 № 273-ФЗ «О противодействии коррупции», ст. 12',
  R05: 'Федеральный закон от 25.12.2008 № 273-ФЗ «О противодействии коррупции», ст. 10',
};

export const flagSeeds: FlagSeed[] = [
  {
    n: 1,
    person: 1,
    rule_code: 'R01',
    severity: 'high',
    weight: 50,
    explanation:
      'Супруга служащего, Соколова М.О., — единственный учредитель ООО «ДорСтройРесурс» (доля 100%). С 2024 по 2026 год ООО заключило 5 контрактов на 86,6 млн ₽ с Министерством строительства и ЖКХ Энской области, где служащий возглавляет отдел государственных закупок и имеет полномочия по закупкам в сфере ОКПД2 41.20, 42.11, 43.99. Один контракт заключён с единственным поставщиком.',
    evidence: [P(1), P(21), C(1), CT(1), CT(2), CT(3), CT(4), CT(5), O(1)],
  },
  {
    n: 2,
    person: 1,
    rule_code: 'R05',
    severity: 'medium',
    weight: 20,
    explanation:
      'Юридический адрес ООО «ДорСтройРесурс» совпадает с адресом регистрации служащего и его супруги: г. Энск, ул. Садовая, д. 14, кв. 37.',
    evidence: [P(1), P(21), C(1)],
  },
  {
    n: 3,
    person: 1,
    rule_code: 'R07',
    severity: 'medium',
    weight: 15,
    explanation:
      'Служащий назван в обращении гражданина с признаками конфликта интересов; обращение конкретное: указаны ФИО, организация, сумма.',
    evidence: [A(1), P(1)],
  },
  {
    n: 4,
    person: 1,
    rule_code: 'R06',
    severity: 'low',
    weight: 8,
    explanation:
      'ООО «ДорСтройРесурс» получило 41% объёма закупок министерства по ОКПД2 41.20/42.11 за 2024–2026 гг. — втрое выше медианы по поставщикам этого сегмента.',
    evidence: [O(1), C(1), CT(1), CT(2), CT(3), CT(4), CT(5)],
  },
  {
    n: 5,
    person: 2,
    rule_code: 'R02',
    severity: 'high',
    weight: 40,
    explanation:
      'Служащая является учредителем действующей коммерческой организации ООО «МедТехСервис» (доля 50%), вторым учредителем и директором выступает её супруг.',
    evidence: [P(2), C(2), P(23)],
  },
  {
    n: 6,
    person: 2,
    rule_code: 'R07',
    severity: 'medium',
    weight: 15,
    explanation: 'Служащая упомянута в обращении о возможном конфликте интересов.',
    evidence: [A(8), P(2)],
  },
  {
    n: 7,
    person: 2,
    rule_code: 'R08',
    severity: 'low',
    weight: 10,
    explanation:
      'Доля закупок у единственного поставщика в курируемом направлении в 2,4 раза выше, чем у коллег на аналогичных должностях в регионе.',
    evidence: [P(2), O(2)],
  },
  {
    n: 8,
    person: 3,
    rule_code: 'R03',
    severity: 'medium',
    weight: 25,
    explanation:
      'До июня 2023 года служащий работал в ООО «ЭнскЛицензКонсалт». После его перехода в администрацию компания получила 2 контракта администрации на 4,25 млн ₽.',
    evidence: [P(3), C(3), CT(6), CT(7), O(3)],
  },
  {
    n: 9,
    person: 3,
    rule_code: 'R08',
    severity: 'low',
    weight: 8,
    explanation:
      'Срок выдачи разрешений заявителям отдельных консультантов вдвое короче среднего по отделу.',
    evidence: [P(3), O(3)],
  },
  {
    n: 10,
    person: 4,
    rule_code: 'R04',
    severity: 'medium',
    weight: 25,
    explanation:
      'Через 2 недели после увольнения с должности начальника отдела муниципального контроля служащий трудоустроен в ООО «ЭнскТеплоМонтаж», в отношении которого его отдел проводил проверки в 2023–2024 гг. Компания получила контракт администрации на 9,7 млн ₽.',
    evidence: [P(4), O(3), C(4), CT(8)],
  },
  {
    n: 11,
    person: 4,
    rule_code: 'R07',
    severity: 'low',
    weight: 10,
    explanation: 'Бывший служащий упомянут в обращении о возможном превышении полномочий.',
    evidence: [A(5), P(4)],
  },
  {
    n: 12,
    person: 5,
    rule_code: 'R07',
    severity: 'medium',
    weight: 20,
    explanation:
      'Служащая упомянута в обращении о вымогательстве «благодарности» за продление договора аренды.',
    evidence: [A(3), P(5)],
  },
  {
    n: 13,
    person: 5,
    rule_code: 'R08',
    severity: 'low',
    weight: 8,
    explanation: 'Доля договоров аренды, продлённых без торгов, выше, чем у коллег отдела.',
    evidence: [P(5), O(4)],
  },
  {
    n: 14,
    person: 6,
    rule_code: 'R06',
    severity: 'low',
    weight: 10,
    explanation:
      'ООО «ДорСтройИнвест» получило 46% объёма закупок управления капитального строительства по ОКПД2 42.11 за 2024–2026 гг.',
    evidence: [O(3), C(6), CT(11), CT(12), CT(13)],
  },
  {
    n: 15,
    person: 6,
    rule_code: 'R08',
    severity: 'low',
    weight: 8,
    explanation: 'Среднее снижение цены на торгах ниже, чем у коллег той же должности в регионе.',
    evidence: [P(6), O(3)],
  },
  {
    n: 16,
    person: 7,
    rule_code: 'R08',
    severity: 'medium',
    weight: 15,
    explanation:
      'Аномальная доля платежей в последние дни финансового года по сравнению с коллегами.',
    evidence: [P(7), O(2)],
  },
  {
    n: 17,
    person: 8,
    rule_code: 'R05',
    severity: 'medium',
    weight: 25,
    explanation:
      'Контактный телефон ООО «Энск-Снаб», поставщика министерства, совпадает с телефоном служащего и его супруги.',
    evidence: [P(8), P(24), C(5), CT(9), CT(10), O(1)],
  },
  {
    n: 18,
    person: 10,
    rule_code: 'R06',
    severity: 'low',
    weight: 10,
    explanation:
      'В курируемом направлении закупок 41% объёма приходится на одного поставщика — ООО «ДорСтройРесурс».',
    evidence: [O(1), C(1), CT(1), CT(2), CT(3), CT(4), CT(5)],
  },
  {
    n: 19,
    person: 11,
    rule_code: 'R08',
    severity: 'low',
    weight: 6,
    explanation: 'Число приватизационных сделок по начальной цене выше, чем у коллег.',
    evidence: [P(11), O(4)],
  },
  {
    n: 20,
    person: 12,
    rule_code: 'R07',
    severity: 'medium',
    weight: 30,
    explanation:
      'Служащий назван в обращении о вымогательстве взятки; обращение очень конкретное: дата, сумма, адрес объекта.',
    evidence: [A(2), P(12)],
  },
  {
    n: 21,
    person: 12,
    rule_code: 'R08',
    severity: 'low',
    weight: 10,
    explanation:
      'Доля проверок без выявленных нарушений заметно выше, чем у других инспекторов отдела.',
    evidence: [P(12), O(3)],
  },
  {
    n: 22,
    person: 13,
    rule_code: 'R03',
    severity: 'medium',
    weight: 25,
    explanation:
      'До августа 2022 года служащая работала в ООО «ГрадПроект»; в 2024 году компания получила контракт администрации на 5,6 млн ₽.',
    evidence: [P(13), C(7), CT(14), O(3)],
  },
  {
    n: 23,
    person: 13,
    rule_code: 'R05',
    severity: 'medium',
    weight: 20,
    explanation:
      'Директор ООО «ГрадПроект» — брат служащей; адрес компании совпадает с адресом его регистрации.',
    evidence: [P(13), P(25), C(7)],
  },
  {
    n: 24,
    person: 15,
    rule_code: 'R06',
    severity: 'low',
    weight: 8,
    explanation:
      'Высокая концентрация бюджетных платежей в адрес одного подрядчика — ООО «ДорСтройИнвест».',
    evidence: [P(15), O(3), C(6)],
  },
];

/* ---------------- Обращения граждан ---------------- */

/** Находит фрагменты в тексте и возвращает сущности с корректными start/end. */
export function findEntities(text: string, specs: [EntityType, string][]): AppealEntity[] {
  const out: AppealEntity[] = [];
  for (const [type, fragment] of specs) {
    const start = text.indexOf(fragment);
    if (start >= 0) out.push({ type, text: fragment, start, end: start + fragment.length });
  }
  return out.sort((a, b) => a.start - b.start);
}

const ROUTE_ANTICORR = 'Отдел по профилактике коррупционных и иных правонарушений';

interface AppealSeed {
  n: number;
  received_at: string;
  channel: Appeal['channel'];
  status: Appeal['status'];
  text: string;
  linked: number[];
  analysis: (Omit<AppealAnalysis, 'entities'> & { entities: [EntityType, string][] }) | null;
}

const appealSeeds: AppealSeed[] = [
  {
    n: 1,
    received_at: '2026-10-28T09:14:00+03:00',
    channel: 'web',
    status: 'routed',
    linked: [1],
    text: 'Сообщаю, что начальник отдела закупок Министерства строительства Энской области Соколов А.В. систематически отдаёт контракты на ремонт дорог и зданий фирме ООО «ДорСтройРесурс», учредителем которой является его жена. Только за 2025 год фирма получила контрактов больше чем на 30 млн рублей. Прошу провести проверку.',
    analysis: {
      is_corruption: true,
      category: 'conflict_of_interest',
      confidence: 0.91,
      specificity: 0.85,
      route_to: ROUTE_ANTICORR,
      summary:
        'Заявитель сообщает о конфликте интересов: начальник отдела закупок Минстроя заключает контракты с компанией супруги.',
      signals: [
        { code: 'named_official', text: 'Назван конкретный служащий' },
        { code: 'named_company', text: 'Названа организация-получатель выгоды' },
        { code: 'kinship', text: 'Указана родственная связь' },
        { code: 'amount', text: 'Указана сумма' },
      ],
      entities: [
        ['position', 'начальник отдела закупок'],
        ['organization', 'Министерства строительства Энской области'],
        ['person', 'Соколов А.В.'],
        ['organization', 'ООО «ДорСтройРесурс»'],
        ['date', '2025 год'],
        ['money', '30 млн рублей'],
      ],
    },
  },
  {
    n: 2,
    received_at: '2026-10-30T16:42:00+03:00',
    channel: 'hotline',
    status: 'analyzed',
    linked: [12],
    text: '15 октября 2026 года инспектор отдела муниципального контроля Фёдоров М.Р. при проверке моего кафе по адресу ул. Ленина, д. 25 потребовал 50 000 рублей, чтобы не выписывать предписание о закрытии. Разговор записан на телефон.',
    analysis: {
      is_corruption: true,
      category: 'bribe',
      confidence: 0.95,
      specificity: 0.95,
      route_to: ROUTE_ANTICORR,
      summary:
        'Сообщение о вымогательстве взятки инспектором муниципального контроля при проверке кафе.',
      signals: [
        { code: 'named_official', text: 'Назван конкретный служащий' },
        { code: 'amount', text: 'Указана сумма' },
        { code: 'date', text: 'Указана дата события' },
        { code: 'evidence', text: 'Заявитель сообщает о наличии записи разговора' },
      ],
      entities: [
        ['date', '15 октября 2026 года'],
        ['position', 'инспектор отдела муниципального контроля'],
        ['person', 'Фёдоров М.Р.'],
        ['address', 'ул. Ленина, д. 25'],
        ['money', '50 000 рублей'],
      ],
    },
  },
  {
    n: 3,
    received_at: '2026-10-21T11:05:00+03:00',
    channel: 'email',
    status: 'analyzed',
    linked: [5],
    text: 'В Комитете по управлению имуществом консультант Волкова О.П. дала понять, что договор аренды нашего помещения будет продлён только за «благодарность». Без этого нам предлагают участвовать в торгах, хотя раньше договор продлевали автоматически.',
    analysis: {
      is_corruption: true,
      category: 'bribe',
      confidence: 0.78,
      specificity: 0.55,
      route_to: ROUTE_ANTICORR,
      summary: 'Намёк на получение незаконного вознаграждения за продление договора аренды.',
      signals: [
        { code: 'named_official', text: 'Назван конкретный служащий' },
        { code: 'veiled_request', text: 'Завуалированное требование вознаграждения' },
      ],
      entities: [
        ['organization', 'Комитете по управлению имуществом'],
        ['position', 'консультант'],
        ['person', 'Волкова О.П.'],
      ],
    },
  },
  {
    n: 4,
    received_at: '2026-10-17T13:30:00+03:00',
    channel: 'letter',
    status: 'routed',
    linked: [],
    text: 'Аукцион Департамента здравоохранения на поставку аппаратов УЗИ проведён с нарушениями: техническое задание написано под оборудование одного производителя, которое поставляет только ООО «ФармаЛайн». Начальная цена 14 200 000 рублей завышена примерно на треть.',
    analysis: {
      is_corruption: true,
      category: 'procurement',
      confidence: 0.82,
      specificity: 0.6,
      route_to:
        'Контрольно-ревизионное управление; копия — в отдел по профилактике коррупционных правонарушений',
      summary: 'Возможное ограничение конкуренции в закупке медицинского оборудования.',
      signals: [
        { code: 'named_company', text: 'Названа организация-поставщик' },
        { code: 'amount', text: 'Указана сумма' },
        { code: 'tailored_spec', text: 'ТЗ «под поставщика»' },
      ],
      entities: [
        ['organization', 'Департамента здравоохранения'],
        ['organization', 'ООО «ФармаЛайн»'],
        ['money', '14 200 000 рублей'],
      ],
    },
  },
  {
    n: 5,
    received_at: '2026-10-12T10:20:00+03:00',
    channel: 'personal',
    status: 'analyzed',
    linked: [4],
    text: 'Бывший начальник отдела муниципального контроля Морозов И.Н. теперь работает в ООО «ЭнскТеплоМонтаж», которое раньше сам проверял. Он звонит бывшим подчинённым и просит не назначать проверки этой компании.',
    analysis: {
      is_corruption: true,
      category: 'abuse_of_power',
      confidence: 0.74,
      specificity: 0.5,
      route_to: ROUTE_ANTICORR,
      summary:
        'Бывший служащий использует связи для влияния на контрольные мероприятия в отношении нового работодателя.',
      signals: [
        { code: 'named_official', text: 'Назван конкретный служащий' },
        { code: 'named_company', text: 'Названа организация' },
        { code: 'revolving_door', text: 'Переход в подконтрольную организацию' },
      ],
      entities: [
        ['position', 'начальник отдела муниципального контроля'],
        ['person', 'Морозов И.Н.'],
        ['organization', 'ООО «ЭнскТеплоМонтаж»'],
      ],
    },
  },
  {
    n: 6,
    received_at: '2026-10-05T08:55:00+03:00',
    channel: 'web',
    status: 'closed',
    linked: [],
    text: 'Во дворе дома по адресу ул. Мира, д. 8 уже две недели не вывозят мусор. Управляющая компания на звонки не отвечает. Просим принять меры.',
    analysis: {
      is_corruption: false,
      category: 'other',
      confidence: 0.97,
      specificity: 0.4,
      route_to: 'Управление ЖКХ администрации г. Энска',
      summary: 'Жалоба на вывоз мусора, признаков коррупции нет.',
      signals: [],
      entities: [['address', 'ул. Мира, д. 8']],
    },
  },
  {
    n: 7,
    received_at: '2026-11-09T19:02:00+03:00',
    channel: 'web',
    status: 'new',
    linked: [],
    text: 'Почему разрешения на строительство в нашем районе получают только «свои» застройщики? Мы подавали документы три раза, и каждый раз отказ по формальным причинам.',
    analysis: null,
  },
  {
    n: 8,
    received_at: '2026-10-24T14:18:00+03:00',
    channel: 'email',
    status: 'analyzed',
    linked: [2],
    text: 'Заместитель руководителя Департамента здравоохранения Петрова Е.С. является совладелицей ООО «МедТехСервис». Прошу проверить, не участвует ли эта фирма в закупках департамента через посредников.',
    analysis: {
      is_corruption: true,
      category: 'conflict_of_interest',
      confidence: 0.84,
      specificity: 0.65,
      route_to: ROUTE_ANTICORR,
      summary:
        'Сообщение о владении служащей долей в коммерческой организации и возможном конфликте интересов.',
      signals: [
        { code: 'named_official', text: 'Назван конкретный служащий' },
        { code: 'named_company', text: 'Названа организация' },
      ],
      entities: [
        ['position', 'Заместитель руководителя'],
        ['organization', 'Департамента здравоохранения'],
        ['person', 'Петрова Е.С.'],
        ['organization', 'ООО «МедТехСервис»'],
      ],
    },
  },
];

export const appeals: Appeal[] = appealSeeds.map((s) => ({
  id: A(s.n),
  received_at: s.received_at,
  channel: s.channel,
  status: s.status,
  text: s.text,
  linked_person_ids: s.linked.map(P),
  analysis: s.analysis
    ? { ...s.analysis, entities: findEntities(s.text, s.analysis.entities) }
    : null,
}));
