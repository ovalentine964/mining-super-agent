import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { usePrices } from '../hooks/usePrices';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

const MINERAL_ICONS: Record<string, string> = { gold: '🥇', copper: '🟤', silver: '⚪' };

interface Props {
  lang: Lang;
}

export default function PriceWidget({ lang }: Props) {
  const t = createTranslator(lang);
  const { data: prices, isLoading, error, refetch } = usePrices();

  return (
    <div className="card card-full">
      <div className="card-header">
        <span className="card-title">{t('prices.title')}</span>
        <span className="badge badge-live">{t('general.live')}</span>
      </div>

      {isLoading && (
        <div className="state-msg">
          <div className="spinner" /><br />{t('prices.loading')}
        </div>
      )}

      {error && (
        <div className="state-msg error-msg">
          {t('prices.error')}{' '}
          <span className="retry-link" onClick={() => refetch()}>{t('general.refresh')}</span>
        </div>
      )}

      {prices && (
        <>
          <div className="price-grid">
            {prices.map((p) => (
              <div className="price-item" key={p.mineral}>
                <div className="price-label">
                  {MINERAL_ICONS[p.mineral] ?? '💎'} {t(`prices.${p.mineral}`) ?? p.mineral}
                </div>
                <div className="price-value">
                  ${p.price_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  <span style={{ fontSize: '0.6em', color: 'var(--text-muted)' }}>{t('prices.perOz')}</span>
                </div>
                <div className={`price-change ${p.change_24h >= 0 ? 'up' : 'down'}`}>
                  {p.change_24h >= 0 ? '▲' : '▼'} {Math.abs(p.change_24h).toFixed(2)}%
                </div>
              </div>
            ))}
          </div>

          {prices[0]?.history && prices[0].history.length > 1 && (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={prices[0].history}>
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 10, fill: '#8b8fa3' }}
                    tickFormatter={(v: string) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#8b8fa3' }} domain={['auto', 'auto']} width={60} />
                  <Tooltip
                    contentStyle={{ background: '#1a1d28', border: '1px solid #2a2e3d', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#8b8fa3' }}
                  />
                  {prices.map((p) => (
                    <Line
                      key={p.mineral}
                      type="monotone"
                      dataKey="price"
                      data={p.history}
                      stroke={p.mineral === 'gold' ? '#ffc107' : p.mineral === 'copper' ? '#e07c3e' : '#c0c0c0'}
                      strokeWidth={2}
                      dot={false}
                      name={p.mineral}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
