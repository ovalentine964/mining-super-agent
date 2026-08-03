import { useQuery } from '@tanstack/react-query';
import { api, RoyaltyDistribution } from '../utils/api';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface Props {
  lang: Lang;
}

export default function RoyaltyCard({ lang }: Props) {
  const t = createTranslator(lang);
  const { data, isLoading, error, refetch } = useQuery<RoyaltyDistribution>({
    queryKey: ['royalties'],
    queryFn: api.getRoyalties,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{t('royalties.title')}</span>
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
        <div className="royalty-stats">
          <div className="royalty-stat">
            <div className="royalty-stat-label">{t('royalties.totalDistributed')}</div>
            <div className="royalty-stat-value" style={{ color: 'var(--accent)' }}>
              ${data.total_distributed_usd.toLocaleString()}
            </div>
          </div>
          <div className="royalty-stat">
            <div className="royalty-stat-label">{t('royalties.communityShare')}</div>
            <div className="royalty-stat-value">{data.community_share_pct}%</div>
          </div>
          <div className="royalty-stat">
            <div className="royalty-stat-label">{t('royalties.pending')}</div>
            <div className="royalty-stat-value" style={{ color: 'var(--yellow)' }}>
              ${data.pending_usd.toLocaleString()}
            </div>
          </div>
          <div className="royalty-stat">
            <div className="royalty-stat-label">{t('royalties.lastDistribution')}</div>
            <div className="royalty-stat-value" style={{ fontSize: '1rem' }}>
              {new Date(data.last_distribution).toLocaleDateString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
