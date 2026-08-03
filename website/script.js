// ===== Sovereign Resource DAO — Live Data Layer =====
// ALL data is REAL. No simulations, no fake numbers.
// Sources: Free commodity APIs, Polygon blockchain, GitHub API.

(function () {
    'use strict';

    // ══════════════════════════════════════════════
    // CONFIGURATION — Update these when contracts deploy
    // ══════════════════════════════════════════════
    const CONFIG = {
        // Polygon mainnet contract addresses (set after deployment)
        // null = not deployed yet → show honest "Pre-Launch" state
        contracts: {
            extractionTracker: null,  // e.g. '0x...'
            royaltyDistributor: null, // e.g. '0x...'
            governanceToken: null,    // e.g. '0x...'
            miningOracle: null,       // e.g. '0x...'
        },
        polygonRpc: 'https://polygon-rpc.com', // Free public RPC
        githubRepo: 'ovalentine964/sovereign-resource-dao',
        // Real commodity price APIs (free, no keys needed)
        priceApis: {
            gold: [
                'https://api.metals.live/v1/spot/gold',
                'https://data-asg.goldprice.org/dbXRates/USD',
            ],
            copper: [
                'https://api.metals.live/v1/spot/copper',
            ],
        },
        refreshInterval: 60_000, // 1 minute
    };

    // ══════════════════════════════════════════════
    // MOBILE NAV
    // ══════════════════════════════════════════════
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobileMenu');
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', () => {
            mobileMenu.classList.toggle('open');
            hamburger.classList.toggle('active');
        });
        mobileMenu.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => {
                mobileMenu.classList.remove('open');
                hamburger.classList.remove('active');
            });
        });
    }

    // ══════════════════════════════════════════════
    // OS DETECTION & DOWNLOAD
    // ══════════════════════════════════════════════
    function detectOS() {
        const ua = navigator.userAgent || '';
        if (/android/i.test(ua)) return 'android';
        if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return 'ios';
        return 'desktop';
    }

    function setupDownloadButtons() {
        const os = detectOS();
        const platformEl = document.getElementById('downloadPlatform');
        const osEl = document.getElementById('downloadOS');
        const heroText = document.getElementById('heroDownloadText');

        if (platformEl) platformEl.textContent = os === 'android' ? 'Android' : os === 'ios' ? 'iOS (Coming Soon)' : 'Android APK';
        if (osEl) osEl.textContent = 'Detected: ' + (os === 'android' ? 'Android' : os === 'ios' ? 'iOS' : 'Desktop');
        if (heroText) heroText.textContent = os === 'android' ? 'Download APK' : os === 'ios' ? 'Coming Soon' : 'Download APK';

        // Fetch latest release from GitHub
        fetch(`https://api.github.com/repos/${CONFIG.githubRepo}/releases/latest`, {
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data) return;
            const apk = (data.assets || []).find(a => a.name && a.name.endsWith('.apk'));
            const url = apk ? apk.browser_download_url : data.html_url;
            if (url) {
                ['mainDownloadBtn', 'heroDownload'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) { el.href = url; el.target = '_blank'; el.rel = 'noopener'; }
                });
            }
        })
        .catch(() => {
            const fallback = `https://github.com/${CONFIG.githubRepo}/releases`;
            ['mainDownloadBtn', 'heroDownload'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.href = fallback;
            });
        });
    }

    // ══════════════════════════════════════════════
    // REAL COMMODITY PRICES
    // ══════════════════════════════════════════════
    const priceState = {
        gold: { current: null, prev: null, history: [] },
        copper: { current: null, prev: null, history: [] },
    };

    async function fetchGoldPrice() {
        // Try metals.live first
        try {
            const res = await fetch(CONFIG.priceApis.gold[0], { signal: AbortSignal.timeout(5000) });
            if (res.ok) {
                const data = await res.json();
                if (data && data.length > 0 && data[0].price) {
                    return parseFloat(data[0].price);
                }
            }
        } catch {}

        // Try goldprice.org
        try {
            const res = await fetch(CONFIG.priceApis.gold[1], { signal: AbortSignal.timeout(5000) });
            if (res.ok) {
                const data = await res.json();
                if (data && data.items && data.items[0]) {
                    return parseFloat(data.items[0].xauPrice);
                }
            }
        } catch {}

        return null;
    }

    async function fetchCopperPrice() {
        try {
            const res = await fetch(CONFIG.priceApis.copper[0], { signal: AbortSignal.timeout(5000) });
            if (res.ok) {
                const data = await res.json();
                if (data && data.length > 0 && data[0].price) {
                    return parseFloat(data[0].price);
                }
            }
        } catch {}
        return null;
    }

    async function fetchAllPrices() {
        const [gold, copper] = await Promise.all([fetchGoldPrice(), fetchCopperPrice()]);

        if (gold !== null) {
            priceState.gold.prev = priceState.gold.current;
            priceState.gold.current = gold;
            priceState.gold.history.push(gold);
            if (priceState.gold.history.length > 20) priceState.gold.history.shift();
        }
        if (copper !== null) {
            priceState.copper.prev = priceState.copper.current;
            priceState.copper.current = copper;
            priceState.copper.history.push(copper);
            if (priceState.copper.history.length > 20) priceState.copper.history.shift();
        }

        renderPrices();
    }

    function formatPrice(val) {
        if (val === null || val === undefined) return '—';
        return '$' + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function renderPrices() {
        const goldEl = document.getElementById('goldPrice');
        const copperEl = document.getElementById('copperPrice');
        const goldChEl = document.getElementById('goldChange');
        const copperChEl = document.getElementById('copperChange');

        if (goldEl) goldEl.textContent = priceState.gold.current ? formatPrice(priceState.gold.current) : 'Fetching...';
        if (copperEl) copperEl.textContent = priceState.copper.current ? formatPrice(priceState.copper.current) : 'Fetching...';

        // Price change %
        if (goldChEl && priceState.gold.current && priceState.gold.prev) {
            const pct = ((priceState.gold.current - priceState.gold.prev) / priceState.gold.prev * 100).toFixed(2);
            goldChEl.textContent = (pct >= 0 ? '+' : '') + pct + '%';
            goldChEl.className = 'dash-change ' + (pct >= 0 ? 'up' : 'down');
        }
        if (copperChEl && priceState.copper.current && priceState.copper.prev) {
            const pct = ((priceState.copper.current - priceState.copper.prev) / priceState.copper.prev * 100).toFixed(2);
            copperChEl.textContent = (pct >= 0 ? '+' : '') + pct + '%';
            copperChEl.className = 'dash-change ' + (pct >= 0 ? 'up' : 'down');
        }

        // Sparklines
        renderSparkline('goldSparkline', priceState.gold.history, '#fdcb6e');
        renderSparkline('copperSparkline', priceState.copper.history, '#00cec9');
    }

    function renderSparkline(containerId, history, color) {
        const container = document.getElementById(containerId);
        if (!container || history.length < 2) return;
        const max = Math.max(...history);
        const min = Math.min(...history);
        const range = max - min || 1;
        container.innerHTML = history.map(v => {
            const h = Math.max(4, ((v - min) / range) * 40);
            return `<div class="spark-bar" style="height:${h}px;background:${color}"></div>`;
        }).join('');
    }

    // ══════════════════════════════════════════════
    // ON-CHAIN STATS (Polygon Smart Contracts)
    // ══════════════════════════════════════════════
    const ABIS = {
        extractionTracker: [
            'function totalExtractions() view returns (uint256)',
            'function verifiedRecords() view returns (uint256)',
        ],
        royaltyDistributor: [
            'function totalDistributed() view returns (uint256)',
        ],
    };

    async function fetchOnChainStats() {
        const stats = {
            extractions: null,
            verified: null,
            distributed: null,
            contractsDeployed: false,
        };

        // Check if any contract is deployed
        const hasContracts = Object.values(CONFIG.contracts).some(addr => addr !== null);
        if (!hasContracts) return stats;

        try {
            // Try loading ethers.js from CDN for client-side contract reads
            if (typeof ethers === 'undefined') {
                await loadScript('https://cdnjs.cloudflare.com/ajax/libs/ethers/6.7.0/ethers.umd.min.js');
            }

            const provider = new ethers.JsonRpcProvider(CONFIG.polygonRpc);
            stats.contractsDeployed = true;

            if (CONFIG.contracts.extractionTracker) {
                const contract = new ethers.Contract(CONFIG.contracts.extractionTracker, ABIS.extractionTracker, provider);
                try {
                    const [total, verified] = await Promise.all([
                        contract.totalExtractions(),
                        contract.verifiedRecords(),
                    ]);
                    stats.extractions = Number(total);
                    stats.verified = Number(verified);
                } catch (e) { console.warn('ExtractionTracker read failed:', e); }
            }

            if (CONFIG.contracts.royaltyDistributor) {
                const contract = new ethers.Contract(CONFIG.contracts.royaltyDistributor, ABIS.royaltyDistributor, provider);
                try {
                    const distributed = await contract.totalDistributed();
                    stats.distributed = Number(ethers.formatEther(distributed));
                } catch (e) { console.warn('RoyaltyDistributor read failed:', e); }
            }
        } catch (e) {
            console.warn('On-chain fetch failed:', e);
        }

        return stats;
    }

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = src;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    // ══════════════════════════════════════════════
    // GITHUB STATS (Real)
    // ══════════════════════════════════════════════
    async function fetchGitHubStats() {
        try {
            const res = await fetch(`https://api.github.com/repos/${CONFIG.githubRepo}`, {
                headers: { 'Accept': 'application/vnd.github.v3+json' },
                signal: AbortSignal.timeout(5000),
            });
            if (!res.ok) return null;
            const data = await res.json();
            return {
                stars: data.stargazers_count || 0,
                forks: data.forks_count || 0,
                watchers: data.subscribers_count || 0,
                openIssues: data.open_issues_count || 0,
            };
        } catch {
            return null;
        }
    }

    // ══════════════════════════════════════════════
    // RENDER ALL DASHBOARD DATA
    // ══════════════════════════════════════════════
    async function updateDashboard() {
        const [onChain, github] = await Promise.all([
            fetchOnChainStats(),
            fetchGitHubStats(),
        ]);

        // Community count
        const communityEl = document.getElementById('communityCount');
        if (communityEl) {
            if (onChain.contractsDeployed && onChain.extractions !== null) {
                communityEl.textContent = onChain.extractions.toLocaleString();
            } else if (github) {
                communityEl.textContent = `${github.stars} GitHub Stars`;
            } else {
                communityEl.textContent = 'Pre-Launch';
            }
        }

        // Fairness index
        const fairnessEl = document.getElementById('fairnessIndex');
        const fairnessMeter = document.getElementById('fairnessMeter');
        if (fairnessEl) {
            if (onChain.contractsDeployed && onChain.verified !== null && onChain.extractions !== null && onChain.extractions > 0) {
                const idx = Math.round((onChain.verified / onChain.extractions) * 100);
                fairnessEl.textContent = idx + ' / 100';
                if (fairnessMeter) fairnessMeter.style.width = idx + '%';
            } else {
                fairnessEl.textContent = 'Awaiting First Extraction';
                if (fairnessMeter) fairnessMeter.style.width = '0%';
            }
        }

        // Stats counters — replace fake data with real
        renderStats(onChain, github);
    }

    function renderStats(onChain, github) {
        const counters = document.querySelectorAll('.stat-value[data-count]');
        counters.forEach(el => {
            const type = el.dataset.statType;
            if (!type) return;

            switch (type) {
                case 'miners':
                    if (github) {
                        el.textContent = github.stars + ' Stars';
                    } else {
                        el.textContent = '0 (Pre-Launch)';
                    }
                    break;
                case 'tracked':
                    if (onChain.contractsDeployed && onChain.extractions !== null) {
                        el.textContent = onChain.extractions.toLocaleString() + ' Records';
                    } else {
                        el.textContent = '0 (Pre-Launch)';
                    }
                    break;
                case 'revenue':
                    if (onChain.contractsDeployed && onChain.distributed !== null) {
                        el.textContent = '$' + onChain.distributed.toLocaleString() + ' Distributed';
                    } else {
                        el.textContent = '$0 (Pre-Launch)';
                    }
                    break;
                case 'nations':
                    el.textContent = '1 (Kenya First)';
                    break;
            }
        });
    }

    // ══════════════════════════════════════════════
    // SCROLL ANIMATIONS
    // ══════════════════════════════════════════════
    function setupScrollAnimations() {
        const elements = document.querySelectorAll('.step, .agent-card, .tech-card, .dash-card');
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
        elements.forEach(el => observer.observe(el));
    }

    // ══════════════════════════════════════════════
    // SMOOTH SCROLL
    // ══════════════════════════════════════════════
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const offset = 80;
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });

    // ══════════════════════════════════════════════
    // NAV SCROLL EFFECT
    // ══════════════════════════════════════════════
    function handleNavScroll() {
        const nav = document.querySelector('.nav');
        if (!nav) return;
        nav.style.background = window.scrollY > 50 ? 'rgba(10,10,15,0.95)' : 'rgba(10,10,15,0.85)';
    }
    window.addEventListener('scroll', handleNavScroll, { passive: true });

    // ══════════════════════════════════════════════
    // INIT — Everything starts here
    // ══════════════════════════════════════════════
    setupDownloadButtons();
    setupScrollAnimations();

    // Fetch real prices immediately, then every 60s
    fetchAllPrices();
    setInterval(fetchAllPrices, CONFIG.refreshInterval);

    // Fetch on-chain + GitHub stats immediately, then every 5 min
    updateDashboard();
    setInterval(updateDashboard, 5 * CONFIG.refreshInterval);

})();
