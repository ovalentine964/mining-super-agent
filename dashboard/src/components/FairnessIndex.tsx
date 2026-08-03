import { useQuery } from '@tanstack/react-query';
import { api, FairnessIndex as FairnessData } from '../utils/api';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface Props {
  lang: Lang;
}

function scoreLabel(score: number, t: (k: string) => string): string {
  if (score >= 80) return t('fairness.excellent');
  if (score >= 60) return t('fairness.good');
  if (score >= 40) return t('fairness.fair');
  return t('fairness.poor');
}

function scoreColor(score: number): string {
  if (score >= 80) return 'var(--accent)';
  if (score >= 60) return 'var(--blue)';
  if (score >= 40) return 'var(--yellow)';
  return 'var(--red)';
}

export default function FairnessIndex({ lang }: Props) {
  const t = createTranslator(lang);
  const { data, isLoading, error, refetch } = useQuery<FairnessData>({
    queryKey: ['fairness-index'],
    queryFn: api.getFairnessIndex,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  const score = data?.score ?? 0;
  const angle = -90 + (score / 100) * 180;
  const radians = (angle * Math.PI) / 180;
  const endX = 90 + 70 * Math.cos(radians);
  const endY = 95 + 70 * Math.sin(radians);
  const largeArc = score > 50 ? 1 : 0;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{t('fairness.title')}</span>
      </div>

      {isLoading && (
        <div className="state-msg">
          <div className="spinner" />
        </div>
      )}

      {error && (
        <div className="state-msg error-msg">
          {t('general.error')}{' '}
          <span className="retry-link" onClick={() => refetch()}>{t('general.refresh')}</span>
        </div>
      )}

      {data && (
        <>
          <div className="gauge-container">
            <svg className="gauge-svg" viewBox="0 0 180 110">
              {/* Background arc */}
              <path
                d="M 20 95 A 70 70 0 0 1 160 95"
                fill="none"
                stroke="var(--border)"
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Value arc */}
              <path
                d={`M 20 95 A 70 70 0 ${largeArc} 1 ${endX} ${endY}`}
                fill="none"
                stroke={scoreColor(score)}
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Needle */}
              <circle cx={endX} cy={endY} r="5" fill={scoreColor(score)} />
            </svg>
            <div className="gauge-label" style={{ color: scoreColor(score) }}>
              {score}/100
            </div>
            <div className="gauge-desc">{scoreLabel(score, t)}</div>
          </div>

          {data.factors && data.factors.length > 0 && (
            <div className="factors-list">
              {data.factors.map((f) => (
                <div className="factor-row" key={f.name}>
                  <span>{f.name}</span>
                  <span style={{ color: scoreColor(f.value), fontWeight: 600 }}>{f.value}%</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
