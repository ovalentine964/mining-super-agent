// ===== Sovereign Resource DAO — Landing Page Script =====
(function () {
    'use strict';

    // ===== MOBILE NAV =====
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

    // ===== OS DETECTION & DOWNLOAD =====
    function detectOS() {
        const ua = navigator.userAgent || '';
        if (/android/i.test(ua)) return 'android';
        if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return 'ios';
        return 'desktop';
    }

    const GITHUB_REPO = 'sovereign-resource-dao/app';
    const GITHUB_RELEASES_API = `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`;

    function setupDownloadButtons() {
        const os = detectOS();
        const platformEl = document.getElementById('downloadPlatform');
        const osEl = document.getElementById('downloadOS');
        const heroText = document.getElementById('heroDownloadText');

        if (platformEl) {
            platformEl.textContent = os === 'android' ? 'Android' : os === 'ios' ? 'iOS (Coming Soon)' : 'Android APK';
        }
        if (osEl) {
            osEl.textContent = 'Detected: ' + (os === 'android' ? 'Android' : os === 'ios' ? 'iOS' : 'Desktop');
        }
        if (heroText) {
            heroText.textContent = os === 'android' ? 'Download APK' : os === 'ios' ? 'Coming Soon' : 'Download APK';
        }

        // Try to resolve latest release
        fetchLatestRelease().then(url => {
            if (url) {
                const btns = [
                    document.getElementById('mainDownloadBtn'),
                    document.getElementById('heroDownload')
                ];
                btns.forEach(btn => {
                    if (btn) {
                        btn.href = url;
                        btn.setAttribute('target', '_blank');
                        btn.setAttribute('rel', 'noopener');
                    }
                });
            }
        }).catch(() => {
            // Fallback: link to releases page
            const fallback = `https://github.com/${GITHUB_REPO}/releases/latest`;
            ['mainDownloadBtn', 'heroDownload'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.href = fallback;
            });
        });
    }

    async function fetchLatestRelease() {
        try {
            const res = await fetch(GITHUB_RELEASES_API, {
                headers: { 'Accept': 'application/vnd.github.v3+json' }
            });
            if (!res.ok) return null;
            const data = await res.json();
            const apkAsset = (data.assets || []).find(a =>
                a.name && a.name.endsWith('.apk')
            );
            if (apkAsset) return apkAsset.browser_download_url;
            // If no APK asset, return the release page itself
            return data.html_url || null;
        } catch {
            return null;
        }
    }

    // ===== LIVE DASHBOARD =====
    const PRICE_BASE = { gold: 3350, copper: 9600 };
    const PRICE_VOLATILITY = { gold: 0.008, copper: 0.015 };
    let goldHistory = [];
    let copperHistory = [];

    function simulatePrice(base, volatility) {
        const change = (Math.random() - 0.5) * 2 * volatility * base;
        return Math.max(base * 0.95, base + change);
    }

    function formatPrice(val, prefix) {
        return prefix + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function updateSparkline(containerId, history, color) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const max = Math.max(...history, 1);
        container.innerHTML = history.map(v => {
            const h = Math.max(4, (v / max) * 40);
            return `<div class="spark-bar" style="height:${h}px;background:${color || 'var(--primary)'}"></div>`;
        }).join('');
    }

    function updateDashboard() {
        // Prices
        const gold = simulatePrice(PRICE_BASE.gold, PRICE_VOLATILITY.gold);
        const copper = simulatePrice(PRICE_BASE.copper, PRICE_VOLATILITY.copper);
        PRICE_BASE.gold = gold;
        PRICE_BASE.copper = copper;

        goldHistory.push(gold);
        copperHistory.push(copper);
        if (goldHistory.length > 20) goldHistory.shift();
        if (copperHistory.length > 20) copperHistory.shift();

        const goldEl = document.getElementById('goldPrice');
        const copperEl = document.getElementById('copperPrice');
        const goldChEl = document.getElementById('goldChange');
        const copperChEl = document.getElementById('copperChange');

        if (goldEl) goldEl.textContent = formatPrice(gold, '$');
        if (copperEl) copperEl.textContent = formatPrice(copper, '$');

        if (goldChEl && goldHistory.length > 1) {
            const pct = ((gold - goldHistory[goldHistory.length - 2]) / goldHistory[goldHistory.length - 2] * 100).toFixed(2);
            goldChEl.textContent = (pct >= 0 ? '+' : '') + pct + '%';
            goldChEl.className = 'dash-change ' + (pct >= 0 ? 'up' : 'down');
        }
        if (copperChEl && copperHistory.length > 1) {
            const pct = ((copper - copperHistory[copperHistory.length - 2]) / copperHistory[copperHistory.length - 2] * 100).toFixed(2);
            copperChEl.textContent = (pct >= 0 ? '+' : '') + pct + '%';
            copperChEl.className = 'dash-change ' + (pct >= 0 ? 'up' : 'down');
        }

        updateSparkline('goldSparkline', goldHistory, '#fdcb6e');
        updateSparkline('copperSparkline', copperHistory, '#00cec9');

        // Community count (slowly growing)
        const communityEl = document.getElementById('communityCount');
        if (communityEl) {
            const base = 847;
            const growth = Math.floor(Date.now() / 60000) % 200;
            communityEl.textContent = (base + growth).toLocaleString();
        }

        // Fairness index
        const fairnessEl = document.getElementById('fairnessIndex');
        const fairnessMeter = document.getElementById('fairnessMeter');
        if (fairnessEl) {
            const idx = (72 + Math.random() * 8).toFixed(1);
            fairnessEl.textContent = idx + ' / 100';
            if (fairnessMeter) fairnessMeter.style.width = idx + '%';
        }
    }

    // Init dashboard with history
    for (let i = 0; i < 12; i++) {
        goldHistory.push(simulatePrice(PRICE_BASE.gold, PRICE_VOLATILITY.gold));
        copperHistory.push(simulatePrice(PRICE_BASE.copper, PRICE_VOLATILITY.copper));
    }
    updateDashboard();
    setInterval(updateDashboard, 5000);

    // ===== ANIMATED COUNTERS =====
    function animateCounters() {
        const counters = document.querySelectorAll('.stat-value[data-count]');
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !entry.target.dataset.animated) {
                    entry.target.dataset.animated = '1';
                    const target = parseInt(entry.target.dataset.count, 10);
                    const prefix = entry.target.dataset.prefix || '';
                    const duration = 2000;
                    const start = performance.now();

                    function step(now) {
                        const elapsed = now - start;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
                        const current = Math.floor(eased * target);
                        entry.target.textContent = prefix + current.toLocaleString('en-US');
                        if (progress < 1) requestAnimationFrame(step);
                        else entry.target.textContent = prefix + target.toLocaleString('en-US');
                    }
                    requestAnimationFrame(step);
                }
            });
        }, { threshold: 0.3 });

        counters.forEach(el => observer.observe(el));
    }

    // ===== SCROLL ANIMATIONS =====
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

    // ===== SMOOTH SCROLL =====
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const offset = 80; // nav height
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });

    // ===== NAV SCROLL EFFECT =====
    function handleNavScroll() {
        const nav = document.querySelector('.nav');
        if (!nav) return;
        if (window.scrollY > 50) {
            nav.style.background = 'rgba(10,10,15,0.95)';
        } else {
            nav.style.background = 'rgba(10,10,15,0.85)';
        }
    }
    window.addEventListener('scroll', handleNavScroll, { passive: true });

    // ===== INIT =====
    setupDownloadButtons();
    animateCounters();
    setupScrollAnimations();

})();
