/**
 * Типы сущностей и ответов API по docs/contracts.md.
 * JSON в snake_case, id — UUID (string), даты — ISO 8601 (string).
 *
 * Поля, помеченные «ДОДУМАНО», в контракте не описаны явно — это наше предположение,
 * его нужно согласовать с бэкендом (см. docs/frontend.md, раздел «Пробелы контракта»).
 */

export type UUID = string;
export type ISODate = string;

/* ---------- Общие ---------- */

export interface Paginated<T> {
  items: T[];
  total: number;
}

/* ---------- Доменная модель ---------- */

export interface Person {
  id: UUID;
  full_name: string;
  inn?: string | null;
  birth_date?: ISODate | null;
  address?: string | null;
  phone?: string | null;
}

export interface Organ {
  id: UUID;
  name: string;
  inn: string;
  region: string;
}

export interface Position {
  id: UUID;
  organ_id: UUID;
  title: string;
  department: string;
  is_corruption_risky: boolean;
}

export interface Appointment {
  id: UUID;
  person_id: UUID;
  position_id: UUID;
  started_at: ISODate;
  ended_at?: ISODate | null;
}

export type AuthorityKind = 'procurement' | 'permits' | 'inspection' | 'budget' | 'hr';

/** ДОДУМАНО: структура scope (в контракте — «коды ОКПД2/ОКВЭД, территория»). */
export interface AuthorityScope {
  okpd2?: string[];
  okved?: string[];
  territory?: string | null;
}

export interface Authority {
  id: UUID;
  position_id: UUID;
  kind: AuthorityKind;
  scope: AuthorityScope;
}

export type KinshipKind = 'spouse' | 'child' | 'parent' | 'sibling' | 'in_law' | 'other';

export interface Kinship {
  id: UUID;
  person_id: UUID;
  relative_id: UUID;
  kind: KinshipKind;
}

export interface Company {
  id: UUID;
  inn: string;
  ogrn: string;
  name: string;
  okved: string;
  address: string;
  phone?: string | null;
  registered_at: ISODate;
  /** ДОДУМАНО: значения статуса. */
  status: 'active' | 'liquidated' | 'liquidating';
}

export type CompanyRoleKind = 'founder' | 'director';

export interface CompanyRole {
  id: UUID;
  company_id: UUID;
  person_id: UUID;
  role: CompanyRoleKind;
  share?: number | null;
  started_at: ISODate;
  ended_at?: ISODate | null;
}

export interface Employment {
  id: UUID;
  person_id: UUID;
  company_id: UUID;
  started_at: ISODate;
  ended_at?: ISODate | null;
}

/** ДОДУМАНО: значения способа закупки. */
export type ProcurementMethod = 'auction' | 'tender' | 'quotation' | 'single_supplier';

export interface Contract {
  id: UUID;
  reg_number: string;
  customer_organ_id: UUID;
  supplier_company_id: UUID;
  amount: number;
  signed_at: ISODate;
  okpd2: string;
  method: ProcurementMethod;
}

export type RuleCode = 'R01' | 'R02' | 'R03' | 'R04' | 'R05' | 'R06' | 'R07' | 'R08';
export type Severity = 'low' | 'medium' | 'high';

/** Узел цепочки доказательств. ДОДУМАНО: формат элемента evidence. node_id совпадает с id узла графа. */
export interface EvidenceItem {
  node_id: UUID;
  type: GraphNodeType;
  label: string;
}

export interface RiskFlag {
  id: UUID;
  person_id: UUID;
  rule_code: RuleCode;
  severity: Severity;
  weight: number;
  explanation: string;
  evidence: EvidenceItem[];
  legal_ref?: string | null;
}

export interface RiskScore {
  person_id: UUID;
  score: number;
  flags_count: number;
  computed_at: ISODate;
}

export type AppealStatus = 'new' | 'analyzed' | 'routed' | 'closed';
export type AppealCategory =
  'bribe' | 'conflict_of_interest' | 'procurement' | 'abuse_of_power' | 'other';
/** ДОДУМАНО: значения канала поступления обращения. */
export type AppealChannel = 'web' | 'email' | 'hotline' | 'letter' | 'personal';

export type EntityType = 'person' | 'organization' | 'position' | 'money' | 'date' | 'address';

export interface AppealEntity {
  type: EntityType;
  text: string;
  start: number;
  end: number;
}

export interface AppealSignal {
  code: string;
  text: string;
}

export interface AppealAnalysis {
  is_corruption: boolean;
  category: AppealCategory;
  confidence: number;
  entities: AppealEntity[];
  signals: AppealSignal[];
  specificity: number;
  route_to: string;
  summary: string;
}

export interface Appeal {
  id: UUID;
  received_at: ISODate;
  channel: AppealChannel;
  text: string;
  status: AppealStatus;
  /** null, пока обращение не проанализировано (status = new). */
  analysis: AppealAnalysis | null;
  linked_person_ids: UUID[];
}

/** ДОДУМАНО: краткая карточка связанного служащего в GET /appeals/{id}. */
export interface LinkedOfficial {
  id: UUID;
  full_name: string;
  position: string;
  organ: string;
  risk_score: number;
}

export interface AppealDetails extends Appeal {
  linked_persons: LinkedOfficial[];
}

export interface ReportDraft {
  id: UUID;
  person_id: UUID;
  text: string;
  created_at: ISODate;
}

/* ---------- Ответы эндпоинтов ---------- */

/** ДОДУМАНО: форма ответа GET /stats/overview. */
export interface StatsOverview {
  officials_total: number;
  officials_with_flags: number;
  flags_by_severity: Record<Severity, number>;
  appeals_total: number;
  appeals_by_status: Record<AppealStatus, number>;
  computed_at: ISODate;
}

/** ДОДУМАНО: краткий флаг для бейджей в рейтинге. */
export interface FlagShort {
  rule_code: RuleCode;
  severity: Severity;
}

/** Элемент GET /officials. ДОДУМАНО: position и organ — строки (название), плюс organ_id. */
export interface OfficialListItem {
  id: UUID;
  full_name: string;
  position: string;
  organ: string;
  organ_id: UUID;
  risk_score: number;
  top_flags: FlagShort[];
}

export type OfficialsSort = '-risk_score' | 'risk_score' | 'full_name' | '-full_name';

export interface OfficialsQuery {
  query?: string;
  organ_id?: UUID;
  min_score?: number;
  sort?: OfficialsSort;
  limit?: number;
  offset?: number;
}

/** ДОДУМАНО: замещение должности, обогащённое должностью и органом. */
export interface AppointmentDetails extends Appointment {
  position: Position;
  organ: Organ;
}

/** ДОДУМАНО: родственник с видом родства. */
export interface RelativeDetails {
  kinship_id: UUID;
  kind: KinshipKind;
  person: Person;
}

/** ДОДУМАНО: компания, связанная со служащим напрямую или через родственника. */
export interface CompanyLink {
  company: Company;
  role: CompanyRoleKind | 'employee';
  share?: number | null;
  /** Через кого связь: сам служащий или родственник. */
  via_person_id: UUID;
  via_person_name: string;
  relation: 'self' | KinshipKind;
  started_at: ISODate;
  ended_at?: ISODate | null;
  contracts_count: number;
  contracts_amount: number;
}

export interface OfficialProfile {
  person: Person;
  appointments: AppointmentDetails[];
  authorities: Authority[];
  relatives: RelativeDetails[];
  companies: CompanyLink[];
  risk: {
    score: number;
    computed_at?: ISODate;
    flags: RiskFlag[];
  };
}

export type GraphNodeType = 'person' | 'company' | 'organ' | 'contract' | 'appeal';

export interface GraphNode {
  id: UUID;
  type: GraphNodeType;
  label: string;
  risk?: number | null;
}

/** ДОДУМАНО: значения edge.type. */
export type GraphEdgeType =
  | 'works_in'
  | 'kinship'
  | 'founder'
  | 'director'
  | 'employment'
  | 'supplier'
  | 'customer'
  | 'mentions';

export interface GraphEdge {
  source: UUID;
  target: UUID;
  type: GraphEdgeType;
  label: string;
}

export interface OfficialGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AppealsQuery {
  status?: AppealStatus;
  category?: AppealCategory;
  limit?: number;
  offset?: number;
}

export interface CreateAppealPayload {
  text: string;
  channel: AppealChannel;
}

/** ДОДУМАНО: ответ POST /risk/recompute. */
export interface RecomputeResult {
  officials_processed: number;
  flags_total: number;
  computed_at: ISODate;
}

/** ДОДУМАНО: набор типов источников ассистента. */
export type AssistantSourceType = 'person' | 'company' | 'organ' | 'contract' | 'appeal' | 'flag';

export interface AssistantSource {
  type: AssistantSourceType;
  id: UUID;
  label: string;
}

export interface AssistantAnswer {
  answer: string;
  sources: AssistantSource[];
}
