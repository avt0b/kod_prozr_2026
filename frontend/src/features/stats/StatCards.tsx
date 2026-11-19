import { Link } from 'react-router';
import type { StatsOverview } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { SEVERITY_LABELS } from '@/shared/lib/labels';

export function StatCards({ stats }: { stats: StatsOverview }) {
  const flagsTotal = Object.values(stats.flags_by_severity).reduce((a, b) => a + b, 0);
  return (
    <section className="stat-grid" aria-label="Сводная статистика">
      <Link to={routes.officials()} className="stat-panel">
        <span className="stat-label">Служащие в системе</span>
        <strong>{stats.officials_total.toLocaleString('ru-RU')}</strong>
        <span className="stat-caption">{stats.officials_with_flags} с флагами риска</span>
        <div className="stat-track" aria-hidden="true">
          <span
            style={{
              width: `${stats.officials_total ? (stats.officials_with_flags / stats.officials_total) * 100 : 0}%`,
            }}
          />
        </div>
      </Link>
      <Link to={routes.riskMap()} className="stat-panel">
        <span className="stat-label">Флаги риска</span>
        <strong>{flagsTotal.toLocaleString('ru-RU')}</strong>
        <div className="stat-severities">
          {(['high', 'medium', 'low'] as const).map((severity) => (
            <span key={severity}>
              <i className={`severity-dot severity-${severity}`} />
              {SEVERITY_LABELS[severity]} <b>{stats.flags_by_severity[severity]}</b>
            </span>
          ))}
        </div>
      </Link>
      <Link to={routes.appeals()} className="stat-panel">
        <span className="stat-label">Обращения граждан</span>
        <strong>{stats.appeals_total.toLocaleString('ru-RU')}</strong>
        <span className="stat-caption">
          {stats.appeals_by_status.analyzed} проанализировано · {stats.appeals_by_status.new} новых
        </span>
        <div className="stat-track" aria-hidden="true">
          <span
            style={{
              width: `${stats.appeals_total ? (stats.appeals_by_status.analyzed / stats.appeals_total) * 100 : 0}%`,
            }}
          />
        </div>
      </Link>
    </section>
  );
}
