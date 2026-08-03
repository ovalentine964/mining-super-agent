import { useExtractions } from '../hooks/useExtractions';
import type { Lang } from '../utils/i18n';
import { createTranslator } from '../utils/i18n';

interface Props {
  lang: Lang;
}

export default function ExtractionTable({ lang }: Props) {
  const t = createTranslator(lang);
  const { data: extractions, isLoading, error, refetch } = useExtractions();

  return (
    <div className="card card-full">
      <div className="card-header">
        <span className="card-title">{t('extractions.title')}</span>
      </div>

      {isLoading && (
        <div className="state-msg">
          <div className="spinner" /><br />{t('extractions.loading')}
        </div>
      )}

      {error && (
        <div className="state-msg error-msg">
          {t('general.error')}{' '}
          <span className="retry-link" onClick={() => refetch()}>{t('general.refresh')}</span>
        </div>
      )}

      {extractions && extractions.length === 0 && (
        <div className="state-msg">{t('extractions.noData')}</div>
      )}

      {extractions && extractions.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t('extractions.date')}</th>
                <th>{t('extractions.mineral')}</th>
                <th>{t('extractions.quantity')}</th>
                <th>{t('extractions.location')}</th>
                <th>{t('extractions.validator')}</th>
              </tr>
            </thead>
            <tbody>
              {extractions.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.date).toLocaleDateString()}</td>
                  <td style={{ textTransform: 'capitalize' }}>{e.mineral}</td>
                  <td>{e.quantity_kg.toLocaleString()}</td>
                  <td>{e.location}</td>
                  <td title={e.validator}>
                    {e.validator.slice(0, 8)}…{e.validator.slice(-4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
