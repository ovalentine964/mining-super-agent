/**
 * ═══════════════════════════════════════════════════════════════
 * Sovereign Resource DAO — Community Dashboard
 * Live data · Bilingual (EN/SW) · Auto-refresh 30s · Mobile
 * ═══════════════════════════════════════════════════════════════
 */

'use strict';

// ── Configuration ────────────────────────────────────────────
const CONFIG = {
  // Set your FastAPI backend URL here. Use '' for same-origin.
  API_BASE: window.__DAO_API_BASE || '',
  REFRESH_INTERVAL: 30_000,   // 30 seconds
  COMMODITIES: ['gold', 'copper', 'silver'],
  STORAGE_KEY: 'dao_dashboard_lang',
};

// ── Internationalization (i18n) ──────────────────────────────
const I18N = {
  en: {
    title: 'Sovereign Resource DAO',
    subtitle: 'Community Dashboard',
    live: 'Live',
    offline: 'Offline',
    loading: 'Loading…',
    lastUpdated: 'Updated',
    errorPrefix: 'Error:',
    retryNow: 'Retry',
    dismiss: '✕',

    // Prices
    mineralPrices: 'Mineral Prices',
    realTime: 'Real-time',
    priceGold: 'Gold',
    priceCopper: 'Copper',
    priceSilver: 'Silver',
    perOz: '/oz',
    perLb: '/lb',
    source: 'Source:',
    cached: '(cached)',

    // KPI Stats
    communityStats: 'Community Overview',
    totalMembers: 'Members',
    totalProposals: 'Proposals',
    activeProposals: 'Active Votes',
    passedProposals: 'Passed',
    totalVotingPower: 'Voting Power',

    // Extraction
    extractionRecords: 'Extraction Records',
    date: 'Date',
    location: 'Location',
    mineral: 'Mineral',
    quantity: 'Quantity',
    status: 'Status',
    noExtractions: 'No extraction records yet',
    verified: 'Verified',
    pending: 'Pending',

    // Royalties
    royaltyDistributions: 'Royalty Distributions',
    recipient: 'Recipient',
    amount: 'Amount',
    type: 'Type',
    txHash: 'Tx Hash',
    noRoyalties: 'No distributions recorded yet',
    community: 'Community',
    elder: 'Elder',
    miner: 'Miner',

    // Governance
    governanceProposals: 'Governance Proposals',
    votesFor: 'For',
    votesAgainst: 'Against',
    endsIn: 'Ends in',
    hours: 'h',
    voters: 'voters',
    noProposals: 'No active proposals',
    createProposal: 'Create Proposal',

    // Fairness
    extractionFairness: 'Extraction Fairness Index',
    fairnessDesc: 'Measures how fair current extraction deals are for the community',
    fair: 'Fair',
    belowMarket: 'Below Market',
    exploitative: 'Exploitative',
    severelyExploitative: 'Severely Exploitative',
    analyzing: 'Analyzing…',

    // Satellite
    satelliteMonitoring: 'Satellite Monitoring',
    recentScans: 'Recent Scans',
    alerts: 'Alerts',
    noAlerts: 'No alerts — all clear',
    cloudCover: 'Cloud cover',
    vegetation: 'Vegetation',
    scanDate: 'Scan date',

    // Footer
    poweredBy: 'Powered by Sovereign Resource DAO',
    autoRefresh: 'Auto-refresh every 30s',
    embedded: 'Embeddable dashboard',
  },

  sw: {
    title: 'DAO ya Rasilimali ya Kujitawala',
    subtitle: 'Dashibodi ya Jamii',
    live: 'Hai',
    offline: 'Nje ya Mtandao',
    loading: 'Inapakia…',
    lastUpdated: 'Imesasishwa',
    errorPrefix: 'Hitilafu:',
    retryNow: 'Jaribu Tena',
    dismiss: '✕',

    // Prices
    mineralPrices: 'Bei ya Madini',
    realTime: 'Wakati Halisi',
    priceGold: 'Dhahabu',
    priceCopper: 'Shaba',
    priceSilver: 'Fedha',
    perOz: '/oz',
    perLb: '/lb',
    source: 'Chanzo:',
    cached: '(imehifadhiwa)',

    // KPI Stats
    communityStats: 'Muhtasari wa Jamii',
    totalMembers: 'Wanajamii',
    totalProposals: 'Mapendekezo',
    activeProposals: 'Kura Zinazoendelea',
    passedProposals: 'Yaliyopita',
    totalVotingPower: 'Nguvu ya Kura',

    // Extraction
    extractionRecords: 'Rekodi za Uchimbaji',
    date: 'Tarehe',
    location: 'Mahali',
    mineral: 'Madini',
    quantity: 'Kiasi',
    status: 'Hali',
    noExtractions: 'Hakuna rekodi za uchimbaji bado',
    verified: 'Imethibitishwa',
    pending: 'Inasubiri',

    // Royalties
    royaltyDistributions: 'Mgawanyo wa Malipo',
    recipient: 'Mpokeaji',
    amount: 'Kiasi',
    type: 'Aina',
    txHash: 'Tx Hash',
    noRoyalties: 'Hakuna malipo yaliyorekodiwa bado',
    community: 'Jamii',
    elder: 'Mzee',
    miner: 'Mchimbaji',

    // Governance
    governanceProposals: 'Mapendekezo ya Utawala',
    votesFor: 'Kwa',
    votesAgainst: 'Dhidi',
    endsIn: 'Inaisha ndani',
    hours: 's',
    voters: 'wahoji',
    noProposals: 'Hakuna mapendekezo yanayoendelea',
    createProposal: 'Unda Pendekezo',

    // Fairness
    extractionFairness: 'Fahirisi ya Uadilifu wa Uchimbaji',
    fairnessDesc: 'Inapima jinsi makubaliano ya uchimbaji yalivyo ya haki kwa jamii',
    fair: 'Ya Haki',
    belowMarket: 'Chini ya Soko',
    exploitative: 'Unyonyaji',
    severelyExploitative: 'Unyonyaji Mkubwa',
    analyzing: 'Inachambua…',

    // Satellite
    satelliteMonitoring: 'Ufuatiliaji wa Satelaiti',
    recentScans: 'Skani za Hivi Karibuni',
    alerts: 'Tahadhari',
    noAlerts: 'Hakuna tahadhari — kila kitu sawa',
    cloudCover: 'Mawingu',
    vegetation: 'Mimea',
    scanDate: 'Tarehe ya skani',

    // Footer
    poweredBy: 'Inaendeshwa na DAO ya Rasilimali ya Kujitawala',
    autoRefresh: 'Kusasisha kiotomatiki kila sekunde 30',
    embedded: 'Dashibodi inayoweza kuingizwa',
  },
};

// ── State ────────────────────────────────────────────────────
let currentLang = localStorage.getItem(CONFIG.STORAGE_KEY) || 'en';
let refreshTimer = null;
let lastFetchTime = null;
let errors = {};

// ── Helpers ──────────────────────────────────────────────────
function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function formatNumber(n, decimals = 2) {
  if (n == null || isNaN(n)) return '—';
  return new Intl.NumberFormat(currentLang === 'sw' ? 'sw-KE' : 'en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

function formatCurrency(n, currency = 'USD') {
  if (n == null || isNaN(n)) return '—';
  return new Intl.NumberFormat(currentLang === 'sw' ? 'sw-KE' : 'en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function formatKES(n) {
  if (n == null || isNaN(n)) return '—';
  return 'KES ' + new Intl.NumberFormat('en-KE').format(Math.round(n));
}

function timeAgo(isoString) {
  if (!isoString) return '';
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (diff < 60) return currentLang === 'sw' ? 'sasa hivi' : 'just now';
  if (diff < 3600) {
    const m = Math.floor(diff / 60);
    return currentLang === 'sw' ? `dakika ${m} zilizopita` : `${m}m ago`;
  }
  if (diff < 86400) {
    const h = Math.floor(diff / 3600);
    return currentLang === 'sw' ? `masaa ${h} yaliyopita` : `${h}h ago`;
  }
  const d = Math.floor(diff / 86400);
  return currentLang === 'sw' ? `siku ${d} zilizopita` : `${d}d ago`;
}

function formatHoursLeft(hours) {
  if (hours == null) return '—';
  if (hours < 1) {
    const m = Math.round(hours * 60);
    return currentLang === 'sw' ? `dakika ${m}` : `${m}m`;
  }
  return `${Math.round(hours)}${t('hours')}`;
}

// ── API Client ───────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const url = `${CONFIG.API_BASE}${endpoint}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    const resp = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }
    return await resp.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw err;
  }
}

async function apiGet(endpoint) {
  return apiFetch(endpoint);
}

async function apiPost(endpoint, body) {
  return apiFetch(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── Skeleton Loaders ─────────────────────────────────────────
function skeletonPriceCard(cls) {
  return `
    <div class="price-card ${cls}">
      <div class="loading-skeleton" style="width:44px;height:44px;border-radius:10px;margin-bottom:0.75rem"></div>
      <div class="loading-skeleton skeleton-text" style="width:50%"></div>
      <div class="loading-skeleton skeleton-value"></div>
      <div class="loading-skeleton skeleton-text" style="width:30%;margin-top:0.5rem"></div>
    </div>`;
}

function skeletonTable(rows = 3) {
  let html = '<div class="table-wrap"><table><tbody>';
  for (let i = 0; i < rows; i++) {
    html += `<tr>
      <td><div class="loading-skeleton skeleton-text" style="width:80%"></div></td>
      <td><div class="loading-skeleton skeleton-text" style="width:60%"></div></td>
      <td><div class="loading-skeleton skeleton-text" style="width:40%"></div></td>
    </tr>`;
  }
  html += '</tbody></table></div>';
  return html;
}

function skeletonBlock(h = 100) {
  return `<div class="loading-skeleton skeleton-block" style="height:${h}px"></div>`;
}

function emptyState(icon, msg) {
  return `<div class="empty-state"><div class="icon">${icon}</div><div class="msg">${msg}</div></div>`;
}

// ── Error Banner ─────────────────────────────────────────────
function showError(key, message) {
  errors[key] = message;
  renderErrors();
}

function clearError(key) {
  delete errors[key];
  renderErrors();
}

function renderErrors() {
  const container = $('#error-container');
  if (!container) return;

  const keys = Object.keys(errors);
  if (keys.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = keys.map(k => `
    <div class="error-banner" data-error-key="${k}">
      <span>⚠️</span>
      <span>${t('errorPrefix')} ${errors[k]}</span>
      <button class="dismiss" onclick="dismissError('${k}')">${t('dismiss')}</button>
    </div>
  `).join('');
}

window.dismissError = function (key) {
  delete errors[key];
  renderErrors();
};

// ── Section: Mineral Prices ──────────────────────────────────
async function fetchPrices() {
  const container = $('#prices-grid');
  if (!container) return;

  // Show skeletons on first load
  if (!container.dataset.loaded) {
    container.innerHTML = CONFIG.COMMODITIES.map(c => skeletonPriceCard(c)).join('');
  }

  try {
    const results = await Promise.allSettled(
      CONFIG.COMMODITIES.map(c => apiGet(`/api/v1/prices/${c}`).catch(() => null))
    );

    let html = '';
    CONFIG.COMMODITIES.forEach((commodity, i) => {
      const r = results[i];
      const cls = commodity;
      const emoji = commodity === 'gold' ? '🥇' : commodity === 'copper' ? '🔶' : '🥈';
      const label = t(`price${commodity.charAt(0).toUpperCase() + commodity.slice(1)}`);
      const unit = commodity === 'copper' ? t('perLb') : t('perOz');

      if (r.status === 'fulfilled' && r.value && r.value.success !== false) {
        const d = r.value;
        const price = d.price_usd ?? d.price ?? 0;
        const source = d.source || 'api';
        const cached = d.cached ? ` ${t('cached')}` : '';

        html += `
          <div class="price-card ${cls}">
            <div class="price-icon">${emoji}</div>
            <div class="price-label">${label}</div>
            <div class="price-value">$${formatNumber(price)}</div>
            <div class="price-change neutral">${unit}</div>
            <div class="price-source">${t('source')} ${source}${cached}</div>
          </div>`;
      } else {
        // Fallback: show card with placeholder
        const err = r.reason?.message || r.value?.error || 'Unavailable';
        html += `
          <div class="price-card ${cls}">
            <div class="price-icon">${emoji}</div>
            <div class="price-label">${label}</div>
            <div class="price-value">—</div>
            <div class="price-change neutral">${unit}</div>
            <div class="price-source text-red">${err}</div>
          </div>`;
      }
    });

    container.innerHTML = html;
    container.dataset.loaded = 'true';
    clearError('prices');
  } catch (err) {
    showError('prices', err.message);
    // Keep existing content if already loaded
    if (!container.dataset.loaded) {
      container.innerHTML = CONFIG.COMMODITIES.map(c => skeletonPriceCard(c)).join('');
    }
  }
}

// ── Section: Community Stats ─────────────────────────────────
async function fetchStats() {
  const container = $('#stats-grid');
  if (!container) return;

  if (!container.dataset.loaded) {
    container.innerHTML = Array(5).fill(0).map(() => `
      <div class="stat-card">
        <div class="loading-skeleton" style="width:36px;height:36px;border-radius:8px;margin:0 auto 0.5rem"></div>
        <div class="loading-skeleton skeleton-value" style="margin:0 auto"></div>
        <div class="loading-skeleton skeleton-text" style="width:60%;margin:0.5rem auto 0"></div>
      </div>`).join('');
  }

  try {
    const data = await apiGet('/dao/stats');

    const stats = [
      { icon: '👥', value: formatNumber(data.total_members, 0), label: t('totalMembers') },
      { icon: '📜', value: formatNumber(data.total_proposals, 0), label: t('totalProposals') },
      { icon: '🗳️', value: formatNumber(data.active_proposals, 0), label: t('activeProposals') },
      { icon: '✅', value: formatNumber(data.passed_proposals, 0), label: t('passedProposals') },
      { icon: '⚡', value: formatNumber(data.total_voting_power, 0), label: t('totalVotingPower') },
    ];

    container.innerHTML = stats.map(s => `
      <div class="stat-card">
        <div class="stat-icon">${s.icon}</div>
        <div class="stat-value">${s.value}</div>
        <div class="stat-label">${s.label}</div>
      </div>`).join('');

    container.dataset.loaded = 'true';
    clearError('stats');
  } catch (err) {
    showError('stats', err.message);
    if (!container.dataset.loaded) {
      container.innerHTML = emptyState('📊', t('loading'));
    }
  }
}

// ── Section: Extraction Records ──────────────────────────────
async function fetchExtractions() {
  const container = $('#extractions-content');
  if (!container) return;

  if (!container.dataset.loaded) {
    container.innerHTML = skeletonTable(4);
  }

  try {
    const data = await apiGet('/api/v1/extractions');
    const records = data.extractions || data.records || data || [];

    if (!Array.isArray(records) || records.length === 0) {
      container.innerHTML = emptyState('⛏️', t('noExtractions'));
      container.dataset.loaded = 'true';
      clearError('extractions');
      return;
    }

    let html = `<div class="table-wrap"><table>
      <thead><tr>
        <th>${t('date')}</th>
        <th>${t('location')}</th>
        <th>${t('mineral')}</th>
        <th>${t('quantity')}</th>
        <th>${t('status')}</th>
      </tr></thead><tbody>`;

    records.slice(0, 20).forEach(r => {
      const statusCls = r.status === 'verified' ? 'text-green' : 'text-gold';
      const statusText = r.status === 'verified' ? t('verified') : t('pending');
      html += `<tr>
        <td>${r.date || r.timestamp || '—'}</td>
        <td>${r.location || '—'}</td>
        <td>${r.mineral || r.mineral_type || '—'}</td>
        <td>${r.quantity ? `${formatNumber(r.quantity, 0)} kg` : '—'}</td>
        <td class="${statusCls}">${statusText}</td>
      </tr>`;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
    container.dataset.loaded = 'true';
    clearError('extractions');
  } catch (err) {
    showError('extractions', err.message);
    if (!container.dataset.loaded) {
      container.innerHTML = emptyState('⛏️', t('noExtractions'));
    }
  }
}

// ── Section: Royalty Distributions ───────────────────────────
async function fetchRoyalties() {
  const container = $('#royalties-content');
  if (!container) return;

  if (!container.dataset.loaded) {
    container.innerHTML = skeletonTable(4);
  }

  try {
    const data = await apiGet('/api/v1/royalties');
    const records = data.distributions || data.royalties || data || [];

    if (!Array.isArray(records) || records.length === 0) {
      container.innerHTML = emptyState('💰', t('noRoyalties'));
      container.dataset.loaded = 'true';
      clearError('royalties');
      return;
    }

    const colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4'];

    let html = '';
    records.slice(0, 15).forEach((r, i) => {
      const name = r.recipient || r.name || r.wallet_address || '—';
      const initials = name.slice(0, 2).toUpperCase();
      const role = r.role || t('community');
      const amount = r.amount_kes ? formatKES(r.amount_kes) : r.amount_usd ? formatCurrency(r.amount_usd) : '—';
      const color = colors[i % colors.length];

      html += `
        <div class="royalty-item">
          <div class="royalty-avatar" style="background:${color}22;color:${color}">${initials}</div>
          <div class="royalty-info">
            <div class="royalty-name">${name}</div>
            <div class="royalty-role">${role}</div>
          </div>
          <div class="royalty-amount">${amount}</div>
        </div>`;
    });

    container.innerHTML = html;
    container.dataset.loaded = 'true';
    clearError('royalties');
  } catch (err) {
    showError('royalties', err.message);
    if (!container.dataset.loaded) {
      container.innerHTML = emptyState('💰', t('noRoyalties'));
    }
  }
}

// ── Section: Governance Proposals ────────────────────────────
async function fetchProposals() {
  const container = $('#proposals-content');
  if (!container) return;

  if (!container.dataset.loaded) {
    container.innerHTML = skeletonBlock(160);
  }

  try {
    const data = await apiGet('/dao/proposals');
    const proposals = data.proposals || [];

    if (proposals.length === 0) {
      container.innerHTML = emptyState('🗳️', t('noProposals'));
      container.dataset.loaded = 'true';
      clearError('proposals');
      return;
    }

    let html = '';
    proposals.forEach(p => {
      const total = (p.for_power || 0) + (p.against_power || 0);
      const forPct = total > 0 ? ((p.for_power || 0) / total * 100) : 50;
      const typeLabel = (p.type || 'general').replace(/_/g, ' ');
      const statusCls = p.status || 'active';

      html += `
        <div class="proposal-card">
          <div class="proposal-meta">
            <span class="proposal-type">${typeLabel}</span>
            <span class="proposal-status ${statusCls}">${p.status || 'active'}</span>
          </div>
          <div class="proposal-title">${p.title || p.id}</div>
          <div class="vote-bar"><div class="vote-bar-fill" style="width:${forPct}%"></div></div>
          <div class="vote-stats">
            <div class="vote-count">
              <span class="for">${t('votesFor')}: ${formatNumber(p.for_power || 0, 1)}</span>
              <span class="against">${t('votesAgainst')}: ${formatNumber(p.against_power || 0, 1)}</span>
            </div>
            <div>
              <span class="time-left">${t('endsIn')} ${formatHoursLeft(p.voting_ends_in_hours)}</span>
              <span class="text-muted"> · ${p.voter_count || 0} ${t('voters')}</span>
            </div>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    container.dataset.loaded = 'true';
    clearError('proposals');
  } catch (err) {
    showError('proposals', err.message);
    if (!container.dataset.loaded) {
      container.innerHTML = emptyState('🗳️', t('noProposals'));
    }
  }
}

// ── Section: Fairness Index ──────────────────────────────────
async function fetchFairness() {
  const gauge = $('#fairness-gauge');
  const valueEl = $('#fairness-value');
  const verdictEl = $('#fairness-verdict');
  const descEl = $('#fairness-desc');

  if (!gauge) return;

  try {
    const data = await apiGet('/fair-deal/valentine');

    // Calculate fairness score: exploitation_ratio mapped to 0-100
    // ratio 1.0 = perfectly fair (100), ratio 0 = totally exploitative (0)
    const ratio = data.exploitation_ratio || 0;
    const score = Math.min(100, Math.round(ratio * 100));

    // Update gauge SVG
    const circumference = 251.2; // half circle
    const offset = circumference - (score / 100) * circumference;
    gauge.style.strokeDashoffset = offset;

    // Color based on score
    let color;
    if (score >= 70) color = '#10b981';
    else if (score >= 40) color = '#f59e0b';
    else if (score >= 15) color = '#ef4444';
    else color = '#dc2626';
    gauge.style.stroke = color;

    // Value
    if (valueEl) valueEl.textContent = score;

    // Verdict
    if (verdictEl) {
      const verdict = data.verdict || 'UNKNOWN';
      let verdictText, verdictCls;
      switch (verdict) {
        case 'FAIR': verdictText = t('fair'); verdictCls = 'fair'; break;
        case 'BELOW_MARKET': verdictText = t('belowMarket'); verdictCls = 'below'; break;
        case 'EXPLOITATIVE': verdictText = t('exploitative'); verdictCls = 'exploitative'; break;
        case 'SEVERELY_EXPLOITATIVE': verdictText = t('severelyExploitative'); verdictCls = 'severe'; break;
        default: verdictText = verdict; verdictCls = 'below';
      }
      verdictEl.textContent = verdictText;
      verdictEl.className = `gauge-verdict ${verdictCls}`;
    }

    // Description
    if (descEl) {
      const explanation = currentLang === 'sw' ? data.explanation_sw : data.explanation_en;
      descEl.textContent = explanation || t('fairnessDesc');
    }

    clearError('fairness');
  } catch (err) {
    showError('fairness', err.message);
    if (valueEl) valueEl.textContent = '—';
    if (verdictEl) { verdictEl.textContent = '—'; verdictEl.className = 'gauge-verdict'; }
  }
}

// ── Section: Satellite Monitoring ────────────────────────────
async function fetchSatellite() {
  const container = $('#satellite-content');
  if (!container) return;

  if (!container.dataset.loaded) {
    container.innerHTML = skeletonBlock(120);
  }

  try {
    const data = await apiGet('/api/v1/satellite/latest');
    const scans = data.scans || data.observations || data || [];
    const alerts = data.alerts || [];

    let html = '';

    // Recent scans
    if (Array.isArray(scans) && scans.length > 0) {
      html += `<div style="margin-bottom:1rem">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-secondary);margin-bottom:0.75rem;text-transform:uppercase;letter-spacing:0.05em">${t('recentScans')}</div>`;

      scans.slice(0, 5).forEach(s => {
        html += `
          <div class="alert-item">
            <div class="alert-icon info">🛰️</div>
            <div class="alert-content">
              <div class="alert-title">${s.location || s.area || 'Scan'}</div>
              <div class="alert-desc">${s.bands || s.type || 'Sentinel-2'} · ${t('cloudCover')}: ${s.cloud_cover != null ? s.cloud_cover + '%' : '—'}</div>
            </div>
            <div class="alert-time">${timeAgo(s.date || s.timestamp)}</div>
          </div>`;
      });
      html += '</div>';
    }

    // Alerts
    const alertList = Array.isArray(alerts) ? alerts : [];
    html += `<div>
      <div style="font-size:0.8rem;font-weight:600;color:var(--text-secondary);margin-bottom:0.75rem;text-transform:uppercase;letter-spacing:0.05em">${t('alerts')}</div>`;

    if (alertList.length === 0) {
      html += `<div style="text-align:center;padding:1rem;color:var(--text-muted);font-size:0.85rem">✅ ${t('noAlerts')}</div>`;
    } else {
      alertList.slice(0, 5).forEach(a => {
        const level = a.severity || a.level || 'info';
        const iconCls = level === 'high' || level === 'critical' ? 'danger' : level === 'warning' ? 'warning' : 'info';
        const emoji = iconCls === 'danger' ? '🚨' : iconCls === 'warning' ? '⚠️' : 'ℹ️';
        html += `
          <div class="alert-item">
            <div class="alert-icon ${iconCls}">${emoji}</div>
            <div class="alert-content">
              <div class="alert-title">${a.title || a.message || 'Alert'}</div>
              <div class="alert-desc">${a.description || a.details || ''}</div>
            </div>
            <div class="alert-time">${timeAgo(a.timestamp || a.date)}</div>
          </div>`;
      });
    }
    html += '</div>';

    container.innerHTML = html;
    container.dataset.loaded = 'true';
    clearError('satellite');
  } catch (err) {
    showError('satellite', err.message);
    if (!container.dataset.loaded) {
      container.innerHTML = emptyState('🛰️', t('loading'));
    }
  }
}

// ── Section: Blockchain Status ───────────────────────────────
async function fetchChainStatus() {
  const badge = $('#chain-status');
  if (!badge) return;

  try {
    const data = await apiGet('/chain/status');
    const connected = data.connected ?? data.status === 'connected' ?? true;
    badge.textContent = connected ? t('live') : t('offline');
    badge.className = `status-badge ${connected ? 'online' : 'offline'}`;
    clearError('chain');
  } catch {
    badge.textContent = t('offline');
    badge.className = 'status-badge offline';
  }
}

// ── Refresh All Sections ─────────────────────────────────────
async function refreshAll() {
  const now = new Date();
  lastFetchTime = now;

  // Update timestamp
  const tsEl = $('#last-updated');
  if (tsEl) {
    tsEl.textContent = `${t('lastUpdated')}: ${now.toLocaleTimeString(currentLang === 'sw' ? 'sw-KE' : 'en-US')}`;
  }

  // Fetch all sections in parallel
  await Promise.allSettled([
    fetchPrices(),
    fetchStats(),
    fetchExtractions(),
    fetchRoyalties(),
    fetchProposals(),
    fetchFairness(),
    fetchSatellite(),
    fetchChainStatus(),
  ]);
}

// ── Language Toggle ──────────────────────────────────────────
function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem(CONFIG.STORAGE_KEY, lang);

  // Update toggle buttons
  $$('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // Update HTML lang attribute
  document.documentElement.lang = lang === 'sw' ? 'sw' : 'en';

  // Re-render all text (data will be re-rendered on next refresh)
  updateStaticText();
  refreshAll();
}

function updateStaticText() {
  // Header
  const titleEl = $('#brand-title');
  const subtitleEl = $('#brand-subtitle');
  if (titleEl) titleEl.textContent = t('title');
  if (subtitleEl) subtitleEl.textContent = t('subtitle');

  // Section titles
  $$('.i18n-title').forEach(el => {
    const key = el.dataset.i18n;
    if (key) el.textContent = t(key);
  });

  // Fairness description
  const fDesc = $('#fairness-section-desc');
  if (fDesc) fDesc.textContent = t('fairnessDesc');

  // Footer
  const footerText = $('#footer-text');
  if (footerText) footerText.textContent = t('poweredBy');

  const footerRefresh = $('#footer-refresh');
  if (footerRefresh) footerRefresh.textContent = t('autoRefresh');
}

// ── Auto-Refresh Timer ───────────────────────────────────────
function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshAll, CONFIG.REFRESH_INTERVAL);
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// Pause refresh when tab is hidden (save resources)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopAutoRefresh();
  } else {
    refreshAll();
    startAutoRefresh();
  }
});

// ── Initialization ───────────────────────────────────────────
function init() {
  // Detect embed mode
  if (window.location.search.includes('embed=1') || window.parent !== window) {
    document.body.classList.add('embedded');
  }

  // Set initial language
  $$('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
    btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
  });

  document.documentElement.lang = currentLang === 'sw' ? 'sw' : 'en';

  // Static text
  updateStaticText();

  // Initial data load
  refreshAll();

  // Start auto-refresh
  startAutoRefresh();

  // Manual refresh button
  const refreshBtn = $('#manual-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      refreshAll();
    });
  }
}

// ── Boot ─────────────────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
