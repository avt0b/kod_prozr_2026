/**
 * In-memory «база» моков: собирает ответы эндпоинтов из нормализованных таблиц seed.ts.
 * Состояние живёт до перезагрузки страницы.
 */
import {
  COMPANY_ROLE_LABELS,
  KINSHIP_LABELS,
  RULE_TITLES,
  SEVERITY_ORDER,
} from '@/shared/lib/labels';
import { formatMoneyShort, shortName } from '@/shared/lib/format';
import type {
  Appeal,
  AppealAnalysis,
  AppealCategory,
  AppealDetails,
  AppealEntity,
  AppointmentDetails,
  AssistantAnswer,
  AssistantSource,
  CompanyLink,
  EvidenceItem,
  GraphEdge,
  GraphNode,
  OfficialGraph,
  OfficialListItem,
  OfficialProfile,
  OfficialsQuery,
  ReportDraft,
  RiskFlag,
  StatsOverview,
  UUID,
} from '../types';
import * as seed from './seed';

/* ---------------- Изменяемое состояние ---------------- */

export const state = {
  appeals: [...seed.appeals],
  reports: [] as ReportDraft[],
  computedAt: '2026-11-10T06:00:00+03:00',
  appealCounter: 100,
  reportCounter: 0,
};

/* ---------------- Индексы ---------------- */

const byId = <T extends { id: string }>(list: T[]) => new Map(list.map((x) => [x.id, x]));
const personsById = byId(seed.persons);
const organsById = byId(seed.organs);
const positionsById = byId(seed.positions);
const companiesById = byId(seed.companies);
const contractsById = byId(seed.contracts);

const officialIds = [...new Set(seed.appointments.map((a) => a.person_id))];
export const isOfficial = (id: UUID) => officialIds.includes(id);

/* ---------------- Глобальный граф ---------------- */

const contractLabel = (id: UUID) => {
  const c = contractsById.get(id)!;
  return `Контракт № …${c.reg_number.slice(-6)} · ${formatMoneyShort(c.amount)}`;
};

function buildGlobalGraph() {
  const nodes = new Map<UUID, GraphNode>();
  const edges: GraphEdge[] = [];
  const add = (n: GraphNode) => nodes.set(n.id, n);

  for (const p of seed.persons) add({ id: p.id, type: 'person', label: shortName(p.full_name) });
  for (const o of seed.organs) add({ id: o.id, type: 'organ', label: o.name });
  for (const c of seed.companies) add({ id: c.id, type: 'company', label: c.name });
  for (const c of seed.contracts) add({ id: c.id, type: 'contract', label: contractLabel(c.id) });

  for (const a of seed.appointments) {
    const pos = positionsById.get(a.position_id)!;
    edges.push({
      source: a.person_id,
      target: pos.organ_id,
      type: 'works_in',
      label: a.ended_at
        ? `${pos.title.toLowerCase()} (до ${a.ended_at.slice(0, 4)})`
        : pos.title.toLowerCase(),
    });
  }
  for (const k of seed.kinships) {
    edges.push({
      source: k.person_id,
      target: k.relative_id,
      type: 'kinship',
      label: KINSHIP_LABELS[k.kind],
    });
  }
  for (const r of seed.companyRoles) {
    edges.push({
      source: r.person_id,
      target: r.company_id,
      type: r.role,
      label: r.share ? `${COMPANY_ROLE_LABELS[r.role]} ${r.share}%` : COMPANY_ROLE_LABELS[r.role],
    });
  }
  for (const e of seed.employments) {
    edges.push({
      source: e.person_id,
      target: e.company_id,
      type: 'employment',
      label: e.ended_at ? `работал(а) до ${e.ended_at.slice(0, 4)}` : 'работает',
    });
  }
  for (const c of seed.contracts) {
    edges.push({
      source: c.supplier_company_id,
      target: c.id,
      type: 'supplier',
      label: 'поставщик',
    });
    edges.push({ source: c.id, target: c.customer_organ_id, type: 'customer', label: 'заказчик' });
  }
  return { nodes, edges };
}

const globalGraph = buildGlobalGraph();

function appealNodes(): GraphNode[] {
  return state.appeals.map((a) => ({
    id: a.id,
    type: 'appeal' as const,
    label: `Обращение от ${new Date(a.received_at).toLocaleDateString('ru-RU')}`,
  }));
}

function appealEdges(): GraphEdge[] {
  return state.appeals.flatMap((a) =>
    a.linked_person_ids.map((pid) => ({
      source: a.id,
      target: pid,
      type: 'mentions' as const,
      label: 'упоминает',
    })),
  );
}

function nodeById(id: UUID): GraphNode | undefined {
  return globalGraph.nodes.get(id) ?? appealNodes().find((n) => n.id === id);
}

/* ---------------- Флаги и баллы ---------------- */

const toFlag = (f: seed.FlagSeed): RiskFlag => ({
  id: seed.FLAG(f.n),
  person_id: seed.P(f.person),
  rule_code: f.rule_code,
  severity: f.severity,
  weight: f.weight,
  explanation: f.explanation,
  legal_ref: seed.LEGAL_REFS[f.rule_code] ?? null,
  evidence: f.evidence
    .map((id): EvidenceItem | null => {
      const n = nodeById(id);
      return n ? { node_id: n.id, type: n.type, label: n.label } : null;
    })
    .filter((x): x is EvidenceItem => x !== null),
});

export function flagsOf(personId: UUID): RiskFlag[] {
  return seed.flagSeeds
    .filter((f) => seed.P(f.person) === personId)
    .map(toFlag)
    .sort((a, b) => SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.weight - a.weight);
}

export const scoreOf = (personId: UUID) =>
  Math.min(
    100,
    flagsOf(personId).reduce((sum, f) => sum + f.weight, 0),
  );

/* ---------------- Служащие ---------------- */

function appointmentsOf(personId: UUID): AppointmentDetails[] {
  return seed.appointments
    .filter((a) => a.person_id === personId)
    .map((a) => {
      const position = positionsById.get(a.position_id)!;
      return { ...a, position, organ: organsById.get(position.organ_id)! };
    })
    .sort(
      (a, b) =>
        (a.ended_at ? 1 : 0) - (b.ended_at ? 1 : 0) || b.started_at.localeCompare(a.started_at),
    );
}

export function officialListItem(personId: UUID): OfficialListItem {
  const person = personsById.get(personId)!;
  const current = appointmentsOf(personId)[0];
  return {
    id: personId,
    full_name: person.full_name,
    position: `${current.position.title}, ${current.position.department.toLowerCase()}`,
    organ: current.organ.name,
    organ_id: current.organ.id,
    risk_score: scoreOf(personId),
    top_flags: flagsOf(personId)
      .slice(0, 3)
      .map((f) => ({ rule_code: f.rule_code, severity: f.severity })),
  };
}

export function listOfficials(q: OfficialsQuery) {
  const needle = q.query?.trim().toLowerCase();
  let items = officialIds.map(officialListItem);
  if (needle) {
    items = items.filter(
      (o) =>
        o.full_name.toLowerCase().includes(needle) || o.position.toLowerCase().includes(needle),
    );
  }
  if (q.organ_id) items = items.filter((o) => o.organ_id === q.organ_id);
  if (q.min_score != null) items = items.filter((o) => o.risk_score >= Number(q.min_score));

  const sort = q.sort ?? '-risk_score';
  const dir = sort.startsWith('-') ? -1 : 1;
  const key = sort.replace('-', '') as 'risk_score' | 'full_name';
  items.sort((a, b) =>
    key === 'risk_score'
      ? dir * (a.risk_score - b.risk_score)
      : dir * a.full_name.localeCompare(b.full_name, 'ru'),
  );

  const offset = Number(q.offset ?? 0);
  const limit = Number(q.limit ?? 20);
  return { items: items.slice(offset, offset + limit), total: items.length };
}

function companiesOf(personId: UUID): CompanyLink[] {
  const relatives = seed.kinships.filter((k) => k.person_id === personId);
  const circle: { id: UUID; relation: CompanyLink['relation'] }[] = [
    { id: personId, relation: 'self' },
    ...relatives.map((k) => ({ id: k.relative_id, relation: k.kind })),
  ];

  const contractsStats = (companyId: UUID) => {
    const list = seed.contracts.filter((c) => c.supplier_company_id === companyId);
    return {
      contracts_count: list.length,
      contracts_amount: list.reduce((s, c) => s + c.amount, 0),
    };
  };

  const links: CompanyLink[] = [];
  for (const member of circle) {
    const name = personsById.get(member.id)!.full_name;
    for (const r of seed.companyRoles.filter((x) => x.person_id === member.id)) {
      links.push({
        company: companiesById.get(r.company_id)!,
        role: r.role,
        share: r.share,
        via_person_id: member.id,
        via_person_name: name,
        relation: member.relation,
        started_at: r.started_at,
        ended_at: r.ended_at,
        ...contractsStats(r.company_id),
      });
    }
  }
  for (const e of seed.employments.filter((x) => x.person_id === personId)) {
    links.push({
      company: companiesById.get(e.company_id)!,
      role: 'employee',
      via_person_id: personId,
      via_person_name: personsById.get(personId)!.full_name,
      relation: 'self',
      started_at: e.started_at,
      ended_at: e.ended_at,
      ...contractsStats(e.company_id),
    });
  }
  return links;
}

export function officialProfile(personId: UUID): OfficialProfile | null {
  if (!isOfficial(personId)) return null;
  const appts = appointmentsOf(personId);
  const positionIds = new Set(appts.map((a) => a.position_id));
  return {
    person: personsById.get(personId)!,
    appointments: appts,
    authorities: seed.authorities.filter((a) => positionIds.has(a.position_id)),
    relatives: seed.kinships
      .filter((k) => k.person_id === personId)
      .map((k) => ({ kinship_id: k.id, kind: k.kind, person: personsById.get(k.relative_id)! })),
    companies: companiesOf(personId),
    risk: { score: scoreOf(personId), computed_at: state.computedAt, flags: flagsOf(personId) },
  };
}

/**
 * Подграф вокруг служащего: обход в ширину на depth+2 шагов (через органы не идём, иначе граф
 * разрастается на весь орган) + все узлы из evidence его флагов + рёбра между попавшими узлами.
 */
export function officialGraph(personId: UUID, depth = 2): OfficialGraph | null {
  if (!isOfficial(personId)) return null;
  const allEdges = [...globalGraph.edges, ...appealEdges()];
  const adjacency = new Map<UUID, UUID[]>();
  for (const e of allEdges) {
    adjacency.set(e.source, [...(adjacency.get(e.source) ?? []), e.target]);
    adjacency.set(e.target, [...(adjacency.get(e.target) ?? []), e.source]);
  }

  const included = new Set<UUID>([personId]);
  let frontier = [personId];
  for (let step = 0; step < depth + 2 && frontier.length; step++) {
    const next: UUID[] = [];
    for (const id of frontier) {
      if (id !== personId && nodeById(id)?.type === 'organ') continue;
      for (const nb of adjacency.get(id) ?? []) {
        if (!included.has(nb)) {
          included.add(nb);
          next.push(nb);
        }
      }
    }
    frontier = next;
  }
  for (const f of flagsOf(personId)) f.evidence.forEach((e) => included.add(e.node_id));

  const nodes = [...included]
    .map(nodeById)
    .filter((n): n is GraphNode => !!n)
    .map((n) => (n.type === 'person' && isOfficial(n.id) ? { ...n, risk: scoreOf(n.id) } : n));
  const edges = allEdges.filter((e) => included.has(e.source) && included.has(e.target));
  return { nodes, edges };
}

/* ---------------- Статистика ---------------- */

export function statsOverview(): StatsOverview {
  const allFlags = officialIds.flatMap(flagsOf);
  const count = <T extends string>(values: T[], keys: T[]) =>
    Object.fromEntries(keys.map((k) => [k, values.filter((v) => v === k).length])) as Record<
      T,
      number
    >;
  return {
    officials_total: officialIds.length,
    officials_with_flags: officialIds.filter((id) => flagsOf(id).length > 0).length,
    flags_by_severity: count(
      allFlags.map((f) => f.severity),
      ['high', 'medium', 'low'],
    ),
    appeals_total: state.appeals.length,
    appeals_by_status: count(
      state.appeals.map((a) => a.status),
      ['new', 'analyzed', 'routed', 'closed'],
    ),
    computed_at: state.computedAt,
  };
}

/* ---------------- Обращения ---------------- */

export function appealDetails(id: UUID): AppealDetails | null {
  const appeal = state.appeals.find((a) => a.id === id);
  if (!appeal) return null;
  return {
    ...appeal,
    linked_persons: appeal.linked_person_ids.map((pid) => {
      const item = officialListItem(pid);
      return {
        id: pid,
        full_name: item.full_name,
        position: item.position,
        organ: item.organ,
        risk_score: item.risk_score,
      };
    }),
  };
}

const CATEGORY_KEYWORDS: [AppealCategory, RegExp][] = [
  ['bribe', /взятк|потребовал|вымога|благодарн|вознагражд|откат|деньг|«помочь»/i],
  ['conflict_of_interest', /жена|муж|супруг|родствен|брат|сестр|учредител|совладел/i],
  ['procurement', /закупк|аукцион|тендер|контракт|техническое задание|поставщик/i],
  ['abuse_of_power', /превыш|давлени|угрож|злоупотреб|незаконн/i],
];

const ROUTES: Record<AppealCategory, string> = {
  bribe: 'Отдел по профилактике коррупционных и иных правонарушений',
  conflict_of_interest: 'Отдел по профилактике коррупционных и иных правонарушений',
  procurement: 'Контрольно-ревизионное управление',
  abuse_of_power: 'Отдел по профилактике коррупционных и иных правонарушений',
  other: 'Общий отдел (по компетенции)',
};

function collectMatches(text: string, re: RegExp, type: AppealEntity['type']): AppealEntity[] {
  return [...text.matchAll(re)].map((m) => ({
    type,
    text: m[0].trim(),
    start: m.index!,
    end: m.index! + m[0].trim().length,
  }));
}

/** Наивный «анализ» для моков: регулярки + сопоставление фамилий со служащими. */
export function analyzeText(text: string): { analysis: AppealAnalysis; linked: UUID[] } {
  const entities: AppealEntity[] = [
    ...collectMatches(
      text,
      /[А-ЯЁ][а-яё]+(?:ов|ев|ин|ын|ова|ева|ина|ына|ский|ская)\s[А-ЯЁ]\.\s?[А-ЯЁ]\./g,
      'person',
    ),
    ...collectMatches(text, /(?:ООО|АО|ПАО|ИП)\s«[^»]+»/g, 'organization'),
    ...collectMatches(
      text,
      /\d[\d\s]*(?:[.,]\d+)?\s?(?:тыс\.|млн|млрд)?\s?(?:руб(?:лей|\.)?|₽)/g,
      'money',
    ),
    ...collectMatches(
      text,
      /\d{1,2}\s(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(?:\s\d{4})?/g,
      'date',
    ),
    ...collectMatches(text, /ул\.\s[А-ЯЁ][а-яё]+(?:,\s?д\.\s?\d+[а-я]?)?/g, 'address'),
  ].sort((a, b) => a.start - b.start);

  const linked = officialIds.filter((id) => {
    const surname = personsById.get(id)!.full_name.split(' ')[0];
    return text.includes(surname);
  });

  const category = CATEGORY_KEYWORDS.find(([, re]) => re.test(text))?.[0] ?? 'other';
  const signals = [
    linked.length || entities.some((e) => e.type === 'person')
      ? { code: 'named_official', text: 'Назван конкретный служащий' }
      : null,
    entities.some((e) => e.type === 'organization')
      ? { code: 'named_company', text: 'Названа организация' }
      : null,
    entities.some((e) => e.type === 'money') ? { code: 'amount', text: 'Указана сумма' } : null,
    entities.some((e) => e.type === 'date') ? { code: 'date', text: 'Указана дата' } : null,
  ].filter((s): s is { code: string; text: string } => s !== null);

  const isCorruption = category !== 'other';
  return {
    linked,
    analysis: {
      is_corruption: isCorruption,
      category,
      confidence: isCorruption ? Math.round((0.6 + 0.08 * signals.length) * 100) / 100 : 0.7,
      entities,
      signals,
      specificity: Math.min(1, signals.length / 4),
      route_to: ROUTES[category],
      summary: isCorruption
        ? `Обращение с признаками коррупции (категория определена по ключевым словам). Найдено сигналов: ${signals.length}.`
        : 'Признаков коррупции не выявлено, обращение направляется по компетенции.',
    },
  };
}

export function createAppeal(text: string, channel: Appeal['channel']): Appeal {
  const { analysis, linked } = analyzeText(text);
  const appeal: Appeal = {
    id: seed.uid(12, ++state.appealCounter),
    received_at: new Date().toISOString(),
    channel,
    text,
    status: 'analyzed',
    analysis,
    linked_person_ids: linked,
  };
  state.appeals = [appeal, ...state.appeals];
  return appeal;
}

export function reanalyzeAppeal(id: UUID): Appeal | null {
  const idx = state.appeals.findIndex((a) => a.id === id);
  if (idx < 0) return null;
  const { analysis, linked } = analyzeText(state.appeals[idx].text);
  const updated: Appeal = {
    ...state.appeals[idx],
    analysis,
    linked_person_ids: [...new Set([...state.appeals[idx].linked_person_ids, ...linked])],
    status: state.appeals[idx].status === 'new' ? 'analyzed' : state.appeals[idx].status,
  };
  state.appeals[idx] = updated;
  return updated;
}

/* ---------------- Докладные ---------------- */

export function createReport(personId: UUID): ReportDraft | null {
  const profile = officialProfile(personId);
  if (!profile) return null;
  const current = profile.appointments[0];
  const flagsText = profile.risk.flags
    .map(
      (f, i) =>
        `${i + 1}. ${RULE_TITLES[f.rule_code]} (${f.rule_code}).\n   ${f.explanation}${f.legal_ref ? `\n   Основание: ${f.legal_ref}.` : ''}`,
    )
    .join('\n\n');

  const text = `ДОКЛАДНАЯ ЗАПИСКА
о наличии признаков возможного конфликта интересов

Начальнику отдела по профилактике коррупционных и иных правонарушений

По результатам автоматизированного анализа сведений о служащих выявлены признаки, требующие проверки, в отношении:

${profile.person.full_name}, ${current.position.title.toLowerCase()} (${current.position.department.toLowerCase()}), ${current.organ.name}.

Интегральный балл риска: ${profile.risk.score} из 100.

Выявленные признаки:

${flagsText || 'Признаки не выявлены.'}

Предлагаю:
1. Запросить у служащего пояснения о мерах по предотвращению конфликта интересов.
2. Проверить сведения, представленные в уведомлениях о возможности возникновения конфликта интересов.
3. При подтверждении — рассмотреть вопрос на заседании комиссии по соблюдению требований к служебному поведению и урегулированию конфликта интересов.

Сведения сформированы автоматически и не являются доказательством правонарушения. Решение принимает уполномоченное должностное лицо.

Дата: ${new Date().toLocaleDateString('ru-RU')}
Аналитик: ____________________`;

  const report: ReportDraft = {
    id: seed.REPORT(++state.reportCounter),
    person_id: personId,
    text,
    created_at: new Date().toISOString(),
  };
  state.reports.push(report);
  return report;
}

/* ---------------- Ассистент ---------------- */

export function assistantAnswer(question: string): AssistantAnswer {
  const q = question.toLowerCase();
  const personSource = (id: UUID): AssistantSource => ({
    type: 'person',
    id,
    label: personsById.get(id)!.full_name,
  });

  if (/родствен|супруг|жен|подрядчик|поставщик/.test(q)) {
    const hits = officialIds.filter((id) =>
      flagsOf(id).some((f) => f.rule_code === 'R01' || f.rule_code === 'R05'),
    );
    return {
      answer:
        `Найдено служащих, у которых родственники или общие контакты связаны с подрядчиками их органа: ${hits.length}.\n\n` +
        hits
          .map((id) => {
            const item = officialListItem(id);
            const flag = flagsOf(id).find((f) => f.rule_code === 'R01' || f.rule_code === 'R05')!;
            return `• ${item.full_name} (${item.position}) — балл ${item.risk_score}. ${flag.explanation}`;
          })
          .join('\n'),
      sources: [
        ...hits.map(personSource),
        ...hits.flatMap((id) =>
          flagsOf(id)
            .filter((f) => f.rule_code === 'R01' || f.rule_code === 'R05')
            .map((f) => ({
              type: 'flag' as const,
              id: f.id,
              label: `${f.rule_code} · ${shortName(personsById.get(id)!.full_name)}`,
            })),
        ),
      ],
    };
  }

  if (/обращени|жалоб|взятк/.test(q)) {
    const hits = state.appeals.filter((a) => a.analysis?.is_corruption);
    return {
      answer: `Обращений с признаками коррупции: ${hits.length}. Из них со ссылкой на конкретного служащего: ${
        hits.filter((a) => a.linked_person_ids.length).length
      }.`,
      sources: hits.map((a) => ({
        type: 'appeal' as const,
        id: a.id,
        label: a.analysis?.summary ?? a.text.slice(0, 80),
      })),
    };
  }

  const top = listOfficials({ sort: '-risk_score', limit: 5 }).items;
  return {
    answer:
      'Это ответ-заглушка из моков. Наибольший риск сейчас у служащих:\n' +
      top.map((o, i) => `${i + 1}. ${o.full_name} — ${o.risk_score} баллов`).join('\n') +
      '\n\nПопробуйте спросить: «покажи служащих, у которых родственники среди подрядчиков их органа» или «сколько обращений о взятках».',
    sources: top.map((o) => personSource(o.id)),
  };
}

export function recompute() {
  state.computedAt = new Date().toISOString();
  return {
    officials_processed: officialIds.length,
    flags_total: seed.flagSeeds.length,
    computed_at: state.computedAt,
  };
}
