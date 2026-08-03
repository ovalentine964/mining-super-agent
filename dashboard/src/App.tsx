import { useState } from 'react';
import Header from './components/Header';
import PriceWidget from './components/PriceWidget';
import ExtractionTable from './components/ExtractionTable';
import RoyaltyCard from './components/RoyaltyCard';
import ProposalList from './components/ProposalList';
import FairnessIndex from './components/FairnessIndex';
import SatelliteAlerts from './components/SatelliteAlerts';
import type { Lang } from './utils/i18n';

export default function App() {
  const [lang, setLang] = useState<Lang>('en');

  return (
    <div className="app">
      <Header lang={lang} setLang={setLang} />
      <main className="dashboard-grid">
        <PriceWidget lang={lang} />
        <RoyaltyCard lang={lang} />
        <FairnessIndex lang={lang} />
        <SatelliteAlerts lang={lang} />
        <ExtractionTable lang={lang} />
        <ProposalList lang={lang} />
      </main>
    </div>
  );
}
