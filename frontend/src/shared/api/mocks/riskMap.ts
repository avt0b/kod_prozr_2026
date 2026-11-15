/**
 * Мок GET /risk-map: собирается из тех же таблиц seed.ts, что рейтинг и профиль,
 * поэтому баллы и флаги совпадают с остальными экранами на моках.
 */
import type {
  AuthorityKind,
  OrganRisk,
  PositionRisk,
  PositionRiskLevel,
  RiskAggregate,
  RiskMap,
  RiskMapQuery,
  RuleCode,
  TypicalRisk,
  UUID,
} from '../types';
import { flagsOf, scoreOf, state } from './db';
import * as seed from './seed';

const AUTHORITY_ORDER: AuthorityKind[] = ['procurement', 'permits', 'inspection', 'budget', 'hr'];

/** Сокращённая копия каталога бэка (stats/domain/position_risk.py). */
const TYPICAL_RISKS: Record<AuthorityKind, Omit<TypicalRisk, 'authority'>[]> = {
  procurement: [
    {
      code: 'procurement_affiliated_supplier',
      title: 'Аффилированный поставщик',
      description:
        'Контракты органа получает компания служащего, его родственника или бывшего работодателя',
      rule_codes: ['R01', 'R03', 'R05'],
      legal_ref: '273-ФЗ ст. 10, 11; 44-ФЗ ст. 31 ч. 1 п. 9',
    },
    {
      code: 'procurement_supplier_capture',
      title: '«Свой» поставщик',
      description: 'Закупки в сфере полномочий раз за разом достаются одному поставщику',
      rule_codes: ['R06'],
      legal_ref: '273-ФЗ ст. 10',
    },
    {
      code: 'procurement_revolving_door',
      title: 'Переход к подрядчику',
      description: 'После увольнения служащий уходит в компанию, с которой заключал контракты',
      rule_codes: ['R04'],
      legal_ref: '273-ФЗ ст. 12',
    },
  ],
  permits: [
    {
      code: 'permits_affiliated_applicant',
      title: 'Разрешения «своим»',
      description:
        'Разрешения и лицензии получают компании, в которых участвует служащий или его родственники',
      rule_codes: ['R02', 'R05'],
      legal_ref: '273-ФЗ ст. 10, 11; 79-ФЗ ст. 17',
    },
    {
      code: 'permits_extortion',
      title: 'Вымогательство при выдаче разрешений',
      description: 'Затягивание сроков и отказы ради незаконного вознаграждения',
      rule_codes: ['R07'],
      legal_ref: 'УК РФ ст. 290',
    },
  ],
  inspection: [
    {
      code: 'inspection_loyalty',
      title: 'Лояльность к проверяемым',
      description:
        'Проверяемая организация связана со служащим или берёт его на работу после увольнения',
      rule_codes: ['R02', 'R04'],
      legal_ref: '273-ФЗ ст. 10, 12',
    },
  ],
  budget: [
    {
      code: 'budget_affiliated_recipient',
      title: 'Бюджетные средства аффилированным лицам',
      description: 'Субсидии и платежи направляются организациям, связанным со служащим',
      rule_codes: ['R02', 'R05'],
      legal_ref: '273-ФЗ ст. 10; БК РФ ст. 306.4',
    },
  ],
  hr: [
    {
      code: 'hr_nepotism',
      title: 'Протекционизм при найме',
      description: 'Приём и продвижение родственников, служба в подчинённости родственнику',
      rule_codes: [],
      legal_ref: '79-ФЗ ст. 16 ч. 1 п. 5',
    },
  ],
};

interface Member {
  id: UUID;
  full_name: string;
  score: number;
  rules: RuleCode[];
}

function aggregate(members: Member[]): RiskAggregate {
  const flagged = members.filter((m) => m.rules.length > 0);
  const counts = new Map<RuleCode, number>();
  for (const m of members) {
    for (const code of new Set(m.rules)) counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  const total = members.length;
  return {
    officials_total: total,
    officials_with_flags: flagged.length,
    flagged_share: total ? Math.round((flagged.length / total) * 1000) / 1000 : 0,
    avg_score: total ? Math.round((members.reduce((s, m) => s + m.score, 0) / total) * 10) / 10 : 0,
    max_score: Math.max(0, ...members.map((m) => m.score)),
    top_rules: [...counts]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([rule_code, count]) => ({ rule_code, count })),
    top_officials: [...flagged]
      .sort((a, b) => b.score - a.score || a.full_name.localeCompare(b.full_name, 'ru'))
      .slice(0, 3)
      .map((m) => ({ id: m.id, full_name: m.full_name, risk_score: m.score })),
  };
}

function riskLevel(kinds: AuthorityKind[], risky: boolean): PositionRiskLevel {
  if (kinds.some((k) => k === 'procurement' || k === 'permits' || k === 'inspection')) {
    return 'high';
  }
  return kinds.length > 0 || risky ? 'medium' : 'low';
}

/** Текущая должность — как в рейтинге моков: действующее назначение с поздним началом. */
function currentPositionId(personId: UUID): UUID {
  const own = seed.appointments
    .filter((a) => a.person_id === personId)
    .sort(
      (a, b) =>
        (a.ended_at ? 1 : 0) - (b.ended_at ? 1 : 0) || b.started_at.localeCompare(a.started_at),
    );
  return own[0].position_id;
}

export function riskMap(q: RiskMapQuery): RiskMap {
  const personIds = [...new Set(seed.appointments.map((a) => a.person_id))];
  const byPosition = new Map<UUID, Member[]>();
  for (const id of personIds) {
    const person = seed.persons.find((p) => p.id === id)!;
    const member: Member = {
      id,
      full_name: person.full_name,
      score: scoreOf(id),
      rules: flagsOf(id).map((f) => f.rule_code),
    };
    const positionId = currentPositionId(id);
    byPosition.set(positionId, [...(byPosition.get(positionId) ?? []), member]);
  }

  const items: PositionRisk[] = [...byPosition].map(([positionId, members]) => {
    const position = seed.positions.find((p) => p.id === positionId)!;
    const organ = seed.organs.find((o) => o.id === position.organ_id)!;
    const kinds = AUTHORITY_ORDER.filter((k) =>
      seed.authorities.some((a) => a.position_id === positionId && a.kind === k),
    );
    return {
      position_id: positionId,
      title: position.title,
      department: position.department,
      organ_id: organ.id,
      organ: organ.name,
      is_corruption_risky: position.is_corruption_risky,
      authorities: kinds,
      risk_level: riskLevel(kinds, position.is_corruption_risky),
      typical_risks: kinds.flatMap((k) => TYPICAL_RISKS[k].map((r) => ({ ...r, authority: k }))),
      ...aggregate(members),
    };
  });
  const filtered = items
    .filter((i) => !q.organ_id || i.organ_id === q.organ_id)
    .sort(
      (a, b) =>
        b.avg_score - a.avg_score ||
        b.max_score - a.max_score ||
        a.organ.localeCompare(b.organ, 'ru') ||
        a.title.localeCompare(b.title, 'ru'),
    );

  const organs: OrganRisk[] = seed.organs
    .map((organ) => {
      const own = filtered.filter((i) => i.organ_id === organ.id);
      const members = [...byPosition]
        .filter(([pid]) => own.some((i) => i.position_id === pid))
        .flatMap(([, m]) => m);
      return { organ_id: organ.id, organ: organ.name, positions_total: own.length, members };
    })
    .filter((o) => o.positions_total > 0)
    .map(({ members, ...o }) => ({ ...o, ...aggregate(members) }))
    .sort((a, b) => b.avg_score - a.avg_score || a.organ.localeCompare(b.organ, 'ru'));

  const offset = Number(q.offset ?? 0);
  const limit = Number(q.limit ?? 100);
  return {
    items: filtered.slice(offset, offset + limit),
    total: filtered.length,
    organs,
    computed_at: state.computedAt,
  };
}
