# Sovereign Resource DAO — Blockchain Sprint 1 Fixes Summary

**Date:** 2026-08-04
**Sprint Goal:** Prepare contracts for Amoy testnet deployment, verify security fixes, add missing tests.

---

## Task 1: Mumbai → Amoy Migration ✅

Polygon Mumbai (chainId 80001) was deprecated April 2024. Updated `hardhat.config.js`:

| Field | Old (Mumbai) | New (Amoy) |
|-------|-------------|------------|
| Network name | `mumbai` | `amoy` |
| RPC URL | `https://polygon-mumbai.g.alchemy.com/v2/demo` | `https://rpc-amoy.polygon.technology` |
| Chain ID | `80001` | `80002` |
| Block explorer key | `polygonMumbai` | `polygonAmoy` |
| Explorer URL | — | `https://amoy.polygonscan.com` |

Added `customChains` entry for the Polygonscan Amoy API endpoint.

**Files changed:** `contracts/hardhat.config.js`

---

## Task 2: Deploy Script Enhancements ✅

Rewrote `contracts/scripts/deploy.js` with:

1. **Multisig prerequisite note** — Warning to deploy multisig FIRST before mainnet
2. **Placeholder address comments** — `devFund`, `communityWallet`, `reserve` marked with `// TODO:` for replacement
3. **Role granting step (§6)** — Automatically grants:
   - `ORACLE_ROLE` on ExtractionTracker → MiningOracle contract
   - `ORACLE_ROLE` on MiningOracle → oracle bridge address (placeholder)
   - `MINTER_ROLE` on GovernanceToken → deployer (placeholder for multisig)
4. **Contract verification step (§8)** — Prints `npx hardhat verify` commands for each contract
5. **Updated network references** — `mumbai` → `amoy` throughout

**Files changed:** `contracts/scripts/deploy.js`

---

## Task 3: GovernanceToken Test Suite ✅

Created `contracts/test/GovernanceToken.test.js` with 4 test groups:

### MAX_SUPPLY enforcement (3 tests)
- Minting up to MAX_SUPPLY succeeds
- Minting beyond MAX_SUPPLY reverts
- Incremental minting that exceeds limit reverts

### Vesting creation (7 tests)
- Creates vesting schedule correctly
- Rejects zero address beneficiary
- Rejects zero amount
- Rejects zero vesting duration
- Rejects cliff > vesting duration
- Rejects duplicate vesting for same address
- Rejects vesting that exceeds MAX_SUPPLY

### Vesting release (5 tests)
- Nothing released before cliff
- Tokens released after cliff
- Full amount released after vesting ends
- Proportional release at midpoint
- Rejects release with no schedule

### Access control (6 tests)
- Deployer has DEFAULT_ADMIN_ROLE
- Deployer has MINTER_ROLE
- Deployer has VESTING_ADMIN
- Non-minter cannot mint
- Non-vesting-admin cannot create vesting
- Admin can grant MINTER_ROLE

**Files created:** `contracts/test/GovernanceToken.test.js` (21 tests total)

---

## Task 4: Contract Fix Verification ✅

Read all 5 `.sol` files and verified each security fix:

### ExtractionTracker.sol
| Fix | ID | Status | Evidence |
|-----|----|--------|----------|
| `setTokenURI` override with `TRACKER_ADMIN` access control | C-1 | ✅ Present | `function setTokenURI(...) public override onlyRole(TRACKER_ADMIN)` at line ~172 |
| `disputeExtraction` access control (`VERIFIER_ROLE`) | H-1 | ✅ Present | `onlyRole(VERIFIER_ROLE)` + existence + state checks at line ~155 |
| `verifyExtraction` status check | — | ✅ Present | `require(record.status == VerificationStatus.UNVERIFIED, "Already processed")` at line ~137 |

### MiningOracle.sol
| Fix | ID | Status | Evidence |
|-----|----|--------|----------|
| `hasSubmitted` mapping for duplicate prevention | C-2 | ✅ Present | `mapping(bytes32 => mapping(address => bool)) public hasSubmitted` + checks in `submitData` |
| Minimum confirmations >= 2 | M-2 | ✅ Present | `require(_required >= 2, "Minimum 2 confirmations required")` in `setRequiredConfirmations` |

### RoyaltyDistributor.sol
| Fix | ID | Status | Evidence |
|-----|----|--------|----------|
| Zero address validation in `initialize` | H-3 | ✅ Present | Three `require(addr != address(0))` checks for dev fund, community wallet, reserve |
| Zero address validation in `updateDestinations` | H-3 | ✅ Present | Zero address checks before each update |
| Pending withdrawals fallback | M-5 | ✅ Present | `mapping(address => uint256) public pendingWithdrawals` + `withdrawPending()` |

### GovernanceToken.sol
| Fix | ID | Status | Evidence |
|-----|----|--------|----------|
| Zero address beneficiary check | H-4 | ✅ Present | `require(beneficiary != address(0))` |
| Zero amount check | H-4 | ✅ Present | `require(amount > 0)` |
| Zero vesting duration check | H-4 | ✅ Present | `require(vestingDuration > 0)` |
| Cliff vs duration check | H-4 | ✅ Present | `require(vestingDuration >= cliffDuration)` |

**All security fixes verified as present.**

---

## Task 5: Slither Static Analysis for CI ✅

### Recommended CI Addition

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run Slither Static Analysis
  uses: crytic/slither-action@v0.4.0
  id: slither
  with:
    target: 'contracts/'
    slither-config: 'contracts/slither.config.json'
    fail-on: 'high'
  continue-on-error: true

- name: Upload Slither Report
  uses: actions/upload-artifact@v4
  with:
    name: slither-report
    path: slither-report.json
```

### Recommended `contracts/slither.config.json`:

```json
{
  "detectors_to_exclude": "naming-convention,solc-version",
  "exclude_informational": true,
  "exclude_low": false,
  "filter_paths": "node_modules,test",
  "json": "slither-report.json"
}
```

### Key Slither Detectors for This Codebase
- `reentrancy-eth` — RoyaltyDistributor.send calls
- `unchecked-send` — verify all .call{value:} patterns
- `arbitrary-from-erc721` — soulbound transfer overrides
- `timestamp-dependence` — vesting calculations
- `centralization` — admin role concentration (intentional for now)

**Files suggested:** `.github/workflows/ci.yml` (add step), `contracts/slither.config.json` (new)

---

## Files Modified/Created This Sprint

| File | Action |
|------|--------|
| `contracts/hardhat.config.js` | Modified — Mumbai → Amoy |
| `contracts/scripts/deploy.js` | Modified — roles, comments, verification |
| `contracts/test/GovernanceToken.test.js` | Created — 21 tests |
| `contracts/ExtractionTracker.sol` | Verified — no changes needed |
| `contracts/MiningOracle.sol` | Verified — no changes needed |
| `contracts/RoyaltyDistributor.sol` | Verified — no changes needed |
| `contracts/GovernanceToken.sol` | Verified — no changes needed |

## Next Steps

1. Run `npx hardhat test` to verify all tests pass
2. Run `npx hardhat compile` to verify compilation on Amoy config
3. Deploy multisig wallet on Amoy
4. Run `npx hardhat run scripts/deploy.js --network amoy`
5. Verify contracts on Amoy Polygonscan
6. Add Slither to CI pipeline
7. Transfer all admin roles to multisig after testnet validation
