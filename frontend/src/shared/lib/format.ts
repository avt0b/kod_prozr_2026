const dateFmt = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});
const dateTimeFmt = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const moneyFmt = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0,
});

export const formatDate = (iso?: string | null) => (iso ? dateFmt.format(new Date(iso)) : '—');
export const formatDateTime = (iso?: string | null) =>
  iso ? dateTimeFmt.format(new Date(iso)) : '—';
export const formatMoney = (amount?: number | null) =>
  amount == null ? '—' : moneyFmt.format(amount);

/** 86 600 000 → «86,6 млн ₽» */
export function formatMoneyShort(amount: number): string {
  if (amount >= 1e9)
    return `${(amount / 1e9).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} млрд ₽`;
  if (amount >= 1e6)
    return `${(amount / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} млн ₽`;
  if (amount >= 1e3)
    return `${(amount / 1e3).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} тыс. ₽`;
  return `${amount} ₽`;
}

export const formatPeriod = (from: string, to?: string | null) =>
  `${formatDate(from)} — ${to ? formatDate(to) : 'н.в.'}`;

export const formatPercent = (value: number) => `${Math.round(value * 100)}%`;

/** «Соколов Андрей Викторович» → «Соколов А.В.» */
export function shortName(fullName: string): string {
  const [last, first, middle] = fullName.split(' ');
  return [last, first ? `${first[0]}.` : '', middle ? `${middle[0]}.` : '']
    .join(' ')
    .replace(/\. /, '.')
    .trim();
}

export type RiskLevel = 'high' | 'medium' | 'low' | 'none';

export function riskLevel(score: number): RiskLevel {
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  if (score > 0) return 'low';
  return 'none';
}

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  high: 'red',
  medium: 'orange',
  low: 'yellow',
  none: 'gray',
};
