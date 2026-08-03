export type Lang = 'en' | 'sw';

const translations: Record<string, Record<Lang, string>> = {
  // Header
  'nav.dashboard': { en: 'Dashboard', sw: 'Dashibodi' },
  'nav.connectWallet': { en: 'Connect Wallet', sw: 'Unganisha Mkoba' },
  'nav.connected': { en: 'Connected', sw: 'Imeunganishwa' },

  // Prices
  'prices.title': { en: 'Mineral Prices (Live)', sw: 'Bei ya Madini (Moja kwa Moja)' },
  'prices.gold': { en: 'Gold', sw: 'Dhahabu' },
  'prices.copper': { en: 'Copper', sw: 'Shaba' },
  'prices.silver': { en: 'Silver', sw: 'Fedha' },
  'prices.perOz': { en: '/oz', sw: '/oz' },
  'prices.loading': { en: 'Loading prices...', sw: 'Inapakia bei...' },
  'prices.error': { en: 'Failed to load prices', sw: 'Imeshindwa kupakia bei' },

  // Extractions
  'extractions.title': { en: 'Extraction Records', sw: 'Rekodi za Uchimbaji' },
  'extractions.date': { en: 'Date', sw: 'Tarehe' },
  'extractions.mineral': { en: 'Mineral', sw: 'Madini' },
  'extractions.quantity': { en: 'Quantity (kg)', sw: 'Kiasi (kg)' },
  'extractions.location': { en: 'Location', sw: 'Mahali' },
  'extractions.validator': { en: 'Validator', sw: 'Mdhibiti' },
  'extractions.loading': { en: 'Loading extractions...', sw: 'Inapakia rekodi...' },
  'extractions.noData': { en: 'No extraction records found', sw: 'Hakuna rekodi za uchimbaji' },

  // Royalties
  'royalties.title': { en: 'Royalty Distributions', sw: 'Mgawo wa Royaliti' },
  'royalties.totalDistributed': { en: 'Total Distributed', sw: 'Jumla Imegawanywa' },
  'royalties.communityShare': { en: 'Community Share', sw: 'Sehemu ya Jamii' },
  'royalties.pending': { en: 'Pending', sw: 'Inasubiri' },
  'royalties.lastDistribution': { en: 'Last Distribution', sw: 'Mgawo wa Mwisho' },

  // Proposals
  'proposals.title': { en: 'Governance Proposals', sw: 'Mapendekezo ya Utawala' },
  'proposals.voteFor': { en: 'Vote For', sw: 'Piga Kura Ya' },
  'proposals.voteAgainst': { en: 'Vote Against', sw: 'Piga Kura Dhidi' },
  'proposals.votesFor': { en: 'Votes For', sw: 'Kura Za' },
  'proposals.votesAgainst': { en: 'Votes Against', sw: 'Kura Dhidi' },
  'proposals.status': { en: 'Status', sw: 'Hali' },
  'proposals.active': { en: 'Active', sw: 'Inaendelea' },
  'proposals.passed': { en: 'Passed', sw: 'Imepita' },
  'proposals.rejected': { en: 'Rejected', sw: 'Imekataliwa' },
  'proposals.loading': { en: 'Loading proposals...', sw: 'Inapakia mapendekezo...' },
  'proposals.noData': { en: 'No proposals found', sw: 'Hakuna mapendekezo' },
  'proposals.connectToVote': { en: 'Connect wallet to vote', sw: 'Unganisha mkoba kupiga kura' },

  // Fairness Index
  'fairness.title': { en: 'Extraction Fairness Index', sw: 'Fahirisi ya Usawa wa Uchimbaji' },
  'fairness.score': { en: 'Fairness Score', sw: 'Alama ya Usawa' },
  'fairness.excellent': { en: 'Excellent', sw: 'Bora Sana' },
  'fairness.good': { en: 'Good', sw: 'Nzuri' },
  'fairness.fair': { en: 'Fair', wastani },
  'fairness.poor': { en: 'Poor', sw: 'Dhaifu' },

  // Satellite Alerts
  'satellite.title': { en: 'Satellite Monitoring Alerts', sw: 'Tahadhari za Ufuatiliaji wa Satelaiti' },
  'satellite.severity': { en: 'Severity', sw: 'Ukali' },
  'satellite.high': { en: 'High', sw: 'Juu' },
  'satellite.medium': { en: 'Medium', sw: 'Wastani' },
  'satellite.low': { en: 'Low', sw: 'Chini' },
  'satellite.loading': { en: 'Loading alerts...', sw: 'Inapakia tahadhari...' },
  'satellite.noAlerts': { en: 'No active alerts', sw: 'Hakuna tahadhari' },

  // General
  'general.refresh': { en: 'Refresh', sw: 'Sasisha' },
  'general.live': { en: 'LIVE', sw: 'MOJA KWA MOJA' },
  'general.lastUpdated': { en: 'Last updated', sw: 'Ilisasishwa' },
  'general.error': { en: 'Something went wrong', sw: 'Kuna hitilafu' },
};

export function t(key: string, lang: Lang): string {
  return translations[key]?.[lang] ?? key;
}

export function createTranslator(lang: Lang) {
  return (key: string) => t(key, lang);
}
