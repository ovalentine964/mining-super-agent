import { useAccount } from 'wagmi';
import { useProposals, useVote } from '../hooks/useProposals';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface Props {
  lang: Lang;
}

export default function ProposalList({ lang }: Props) {
  const t = createTranslator(lang);
  const { address, isConnected } = useAccount();
  const { data: proposals, isLoading, error, refetch } = useProposals();
  const voteMutation = useVote();

  const handleVote = (proposalId: string, support: boolean) => {
    if (!address) return;
    voteMutation.mutate({ proposalId, support, voter: address });
  };

  return (
    <div className="card card-full">
      <div className="card-header">
        <span className="card-title">{t('proposals.title')}</span>
      </div>

      {isLoading && (
        <div className="state-msg">
          <div className="spinner" /><br />{t('proposals.loading')}
        </div>
      )}

      {error && (
        <div className="state-msg error-msg">
          {t('general.error')}{' '}
          <span className="retry-link" onClick={() => refetch()}>{t('general.refresh')}</span>
        </div>
      )}

      {proposals && proposals.length === 0 && (
        <div className="state-msg">{t('proposals.noData')}</div>
      )}

      {proposals?.map((p) => {
        const total = p.votes_for + p.votes_against;
        const forPct = total > 0 ? (p.votes_for / total) * 100 : 50;

        return (
          <div className="proposal-item" key={p.id}>
            <div className="proposal-header">
              <span className="proposal-title">{p.title}</span>
              <span className={`status ${p.status}`}>{t(`proposals.${p.status}`)}</span>
            </div>
            <div className="proposal-desc">{p.description}</div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              <span>{t('proposals.votesFor')}: {p.votes_for.toLocaleString()}</span>
              <span>{t('proposals.votesAgainst')}: {p.votes_against.toLocaleString()}</span>
            </div>

            <div className="proposal-votes">
              <div className="vote-bar">
                <div className="vote-bar-fill for" style={{ width: `${forPct}%` }} />
              </div>
              <div className="vote-bar">
                <div className="vote-bar-fill against" style={{ width: `${100 - forPct}%` }} />
              </div>
            </div>

            {p.status === 'active' && (
              <div className="proposal-actions">
                {isConnected ? (
                  <>
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={voteMutation.isPending}
                      onClick={() => handleVote(p.id, true)}
                    >
                      {t('proposals.voteFor')} ✓
                    </button>
                    <button
                      className="btn btn-outline btn-sm"
                      disabled={voteMutation.isPending}
                      onClick={() => handleVote(p.id, false)}
                    >
                      {t('proposals.voteAgainst')} ✕
                    </button>
                  </>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    🔗 {t('proposals.connectToVote')}
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
