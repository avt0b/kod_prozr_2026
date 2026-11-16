import type {
  CompanyLink,
  EvidenceItem,
  OfficialListItem,
  OfficialProfile,
  Organ,
  Position,
  RiskFlag,
} from './types';

export type WireFlag = Omit<RiskFlag, 'evidence'> & {
  evidence: (EvidenceItem | { id: string; type: EvidenceItem['type']; label: string })[];
};
export function normalizeFlag(flag: WireFlag): RiskFlag {
  return {
    ...flag,
    evidence: flag.evidence.map((e) => ({ ...e, node_id: 'node_id' in e ? e.node_id : e.id })),
  };
}
export type WireListItem = Omit<OfficialListItem, 'position' | 'organ'> & {
  position: string | Position | null;
  organ: string | Organ | null;
};
export function normalizeOfficial(item: WireListItem): OfficialListItem {
  return {
    ...item,
    position:
      typeof item.position === 'string'
        ? item.position
        : (item.position?.title ?? 'Должность не указана'),
    organ: typeof item.organ === 'string' ? item.organ : (item.organ?.name ?? 'Орган не указан'),
    organ_id: typeof item.organ === 'object' && item.organ ? item.organ.id : item.organ_id,
  };
}
interface WireCompany {
  person_id: string;
  company_id: string;
  company_name: string;
  company_inn: string;
  company_status: CompanyLink['company']['status'];
  role: CompanyLink['role'];
  share?: number | null;
  started_at: string;
  ended_at?: string | null;
}
export type WireProfile = Omit<OfficialProfile, 'companies'> & {
  companies: (CompanyLink | WireCompany)[];
};
/** Compatibility with checked-in backend DTOs. Unavailable totals stay absent. */
export function normalizeProfile(profile: WireProfile, flags: WireFlag[]): OfficialProfile {
  return {
    ...profile,
    appointments: [...profile.appointments]
      .sort(
        (a, b) =>
          Number(!!a.ended_at) - Number(!!b.ended_at) || b.started_at.localeCompare(a.started_at),
      )
      .map((a) => ({
        ...a,
        person_id: profile.person.id,
        position_id: a.position.id,
      })),
    risk: { ...profile.risk, flags: flags.map(normalizeFlag) },
    companies: profile.companies.map((link): CompanyLink => {
      if ('company' in link) return link;
      const relative = profile.relatives.find((r) => r.person.id === link.person_id);
      return {
        company: {
          id: link.company_id,
          name: link.company_name,
          inn: link.company_inn,
          status: link.company_status,
          ogrn: '',
          okved: '',
          address: '',
          registered_at: '',
        },
        role: link.role,
        share: link.share,
        via_person_id: link.person_id,
        via_person_name: relative?.person.full_name ?? profile.person.full_name,
        relation: relative?.kind ?? 'self',
        started_at: link.started_at,
        ended_at: link.ended_at,
      };
    }),
  };
}
