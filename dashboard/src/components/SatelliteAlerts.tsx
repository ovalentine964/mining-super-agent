import { useQuery } from '@tanstack/react-query';
import { api, SatelliteAlert } from '../utils/api';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface Props {
  lang: Lang;
}

export default function SatelliteAlerts({ lang }: Props) {
  const t = createTranslator(lang);
  const { data: alerts, isLoading, error, refetch } = useQuery<SatelliteAlert[]>({
    queryKey: ['satellite-alerts'],
    queryFn: api.getSatelliteAlerts,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{t('satellite.title')}</span>
      </div>

      {isLoading && (
        <div className="state-msg">
          <div className="spinner" /><br />{t('satellite.loading')}
        </div>
      )}

      {error && (
        <div className="state-msg error-msg">
          {t('general.error')}{' '}
          <span className="retry-link" onClick={() => refetch()}>{t('general.refresh')}</span>
        </div>
      )}

      {alerts && alerts.length === 0 && (
        <div className="state-msg">✅ {t('satellite.noAlerts')}</div>
      )}

      {alerts?.map((a) => (
        <div className="alert-item" key={a.id}>
          <div className={`alert-dot ${a.severity}`} />
          <div className="alert-body">
            <div className="alert-title">{a.type}</div>
            <div className="alert-desc">{a.description}</div>
            <div className="alert-meta">
              📍 {a.location} · {new Date(a.detected_at).toLocaleString()} ·{' '}
              <span style={{ fontWeight: 600, textTransform: 'uppercase' }}>
                {t(`satellite.${a.severity}`)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
