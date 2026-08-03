# Website Council — Sprint 1 Audit Report

**Date:** 2026-08-04
**Auditor:** Website Council (subagent)
**Scope:** `docs/` and `website/` website files for Sovereign Resource DAO

---

## ✅ PASSED: script.js Data Sources

| Check | Status | Detail |
|-------|--------|--------|
| `https://api.metals.live/v1/spot/gold` | ✅ | Used as primary gold price source (line 99) |
| `https://api.github.com/repos/ovalentine964/sovereign-resource-dao` | ✅ | Used via `CONFIG.githubRepo` variable (line 21), called at lines 74 and 282 |
| `https://polygon-rpc.com` | ✅ | Set as `CONFIG.polygonRpc` (line 23) |
| No `simulatePrice` | ✅ | Not found |
| No `12847` | ✅ | Not found |
| No `342918` | ✅ | Not found |
| No `8200000` | ✅ | Not found |
| `fetchOnChainStats()` function | ✅ | Present at line 178, reads from smart contracts via ethers.js |
| Honest fallbacks | ✅ | Uses "Pre-Launch" and "Fetching..." throughout |

---

## ✅ PASSED: index.html Honest Content

| Check | Status | Detail |
|-------|--------|--------|
| "The Problem" with 426B KES | ✅ | Line ~103 |
| 91% stat | ✅ | Line ~107 |
| 1M vs 97M stat | ✅ | Line ~111 |
| `data-stat-type` attributes | ✅ | 4 stat elements (miners, tracked, revenue, nations) at lines 165-177 |
| Links to `ovalentine964/sovereign-resource-dao` | ✅ | Footer GitHub link correct |
| Hero badge says "In Development" | ✅ | Line 46: `🔧 In Development — AI + Blockchain for Mining Communities` |
| FAQ says "targeting Nyatike, Migori County" | ✅ | Line 226 |
| No `sovereign-resource-dao/app` in docs/ or website/ | ✅ | Not found in main files |
| No "Now Live" | ✅ | Not found |
| No "14 African nations" | ✅ | Not found |

---

## ✅ PASSED: docs/ matches website/

```
diff docs/index.html website/index.html  → identical (exit 0)
diff docs/script.js website/script.js    → identical (exit 0)
```

---

## ✅ PASSED: Live Site

`curl https://ovalentine964.github.io/sovereign-resource-dao/` returns the correct HTML. The live site matches `docs/index.html`. Hero badge shows "In Development".

---

## 🐛 BUG FOUND: Stat Counters Selector Mismatch

**Severity:** Medium — stat counters will never update from "Loading..."

**Problem:**
- `docs/script.js` line 339: `document.querySelectorAll('.stat-value[data-count]')`
- `docs/index.html` lines 165-177: elements have `data-stat-type` attribute, NOT `data-count`

The JS queries `[data-count]` but the HTML uses `[data-stat-type]`. The `renderStats()` function finds zero elements and the 4 community stats remain as "Loading..." forever.

**Fix:** Change line 339 in `docs/script.js` (and `website/script.js`):
```js
// FROM:
const counters = document.querySelectorAll('.stat-value[data-count]');
// TO:
const counters = document.querySelectorAll('.stat-value[data-stat-type]');
```

---

## 📁 Stale Files: `docs/docs_site/`

A `docs/docs_site/` directory exists with old content that references the **wrong** GitHub repo:
- `docs/docs_site/script.js` line 29: `const GITHUB_REPO = 'sovereign-resource-dao/app'` (should be `ovalentine964/sovereign-resource-dao`)
- `docs/docs_site/index.html` line 242: links to `sovereign-resource-dao/app/releases`

These files are not served by GitHub Pages (which serves from `docs/` root), but should be cleaned up or removed to avoid confusion.

---

## Summary

| Category | Status |
|----------|--------|
| Real data sources (no fake numbers) | ✅ PASS |
| Honest content (no inflated claims) | ✅ PASS |
| docs/ matches website/ | ✅ PASS |
| Live site deploys correctly | ✅ PASS |
| Stat counters actually work | 🐛 **BUG** — selector mismatch |
| Stale docs_site/ files | ⚠️ Cleanup needed |

**Priority fix:** Change `[data-count]` → `[data-stat-type]` in both `docs/script.js` and `website/script.js`.
