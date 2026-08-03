const API_BASE = '/api';

export interface MineralPrice {
  mineral: string;
  price_usd: number;
  change_24h: number;
  timestamp: string;
  history: { timestamp: string; price: number }[];
}

export interface ExtractionRecord {
  id: string;
  date: string;
  mineral: string;
  quantity_kg: number;
  location: string;
  validator: string;
  tx_hash: string;
}

export interface RoyaltyDistribution {
  total_distributed_usd: number;
  community_share_pct: number;
  pending_usd: number;
  last_distribution: string;
  distributions: { recipient: string; amount: number; date: string }[];
}

export interface Proposal {
  id: string;
  title: string;
  description: string;
  votes_for: number;
  votes_against: number;
  status: 'active' | 'passed' | 'rejected';
  deadline: string;
  proposer: string;
}

export interface SatelliteAlert {
  id: string;
  severity: 'high' | 'medium' | 'low';
  type: string;
  description: string;
  location: string;
  detected_at: string;
  coordinates: { lat: number; lng: number };
}

export interface FairnessIndex {
  score: number;
  factors: { name: string; value: number }[];
  trend: { date: string; score: number }[];
}

async function fetchJSON<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getPrices: () => fetchJSON<MineralPrice[]>('/prices'),
  getExtractions: () => fetchJSON<ExtractionRecord[]>('/extractions'),
  getRoyalties: () => fetchJSON<RoyaltyDistribution>('/royalties'),
  getProposals: () => fetchJSON<Proposal[]>('/proposals'),
  getFairnessIndex: () => fetchJSON<FairnessIndex>('/fairness-index'),
  getSatelliteAlerts: () => fetchJSON<SatelliteAlert[]>('/satellite-alerts'),
  voteOnProposal: (proposalId: string, support: boolean, voter: string) =>
    fetch(`${API_BASE}/proposals/${proposalId}/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ support, voter }),
    }).then(r => {
      if (!r.ok) throw new Error(`Vote failed: ${r.status}`);
      return r.json();
    }),
};

export const WS_URL =
  import.meta.env.DEV
    ? `ws://${window.location.host}/ws`
    : `wss://${window.location.host}/ws`;
