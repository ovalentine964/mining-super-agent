# Sovereign Resource DAO — Smart Contract Analysis Report

**Date:** 2026-08-04
**Scope:** All `.sol` contracts, `hardhat.config.js`, `deploy.js`, and test files
**Contracts Reviewed:** GovernanceToken, ExtractionTracker, MiningOracle, QuadraticVoting, RoyaltyDistributor
**Solidity Version:** ^0.8.20

---

## 1. Contract Architecture & Design Patterns

### 1.1 Overview

The system consists of five contracts implementing a DAO for mineral resource governance:

| Contract | Base | Purpose |
|----------|------|---------|
| **GovernanceToken** ($MINE) | ERC20 + ERC20Votes + ERC20Permit + AccessControl | Governance token with vesting |
| **ExtractionTracker** | ERC721URIStorage (Soulbound) + AccessControl | Immutable extraction records |
| **MiningOracle** | AccessControl | Multi-oracle mineral data verification |
| **QuadraticVoting** | AccessControl + ReentrancyGuard | Quadratic voting mechanism |
| **RoyaltyDistributor** | UUPSUpgradeable + AccessControlUpgradeable + ReentrancyGuard | Revenue splitting |

### 1.2 Design Patterns Used

- **Role-Based Access Control (RBAC):** All contracts use OpenZeppelin `AccessControl` with well-defined roles (`MINTER_ROLE`, `ORACLE_ROLE`, `VERIFIER_ROLE`, `DAO_ROLE`, etc.)
- **Soulbound NFTs:** ExtractionTracker overrides `_beforeTokenTransfer` to prevent transfers while allowing minting
- **UUPS Proxy:** RoyaltyDistributor uses upgradeable proxy pattern for governance-gated upgrades
- **Checks-Effects-Interactions:** Generally followed in `castVote` and `withdrawVote`
- **Multi-oracle Consensus:** MiningOracle requires N confirmations before verifying a location
- **Optimistic Updates:** Voting totals updated before token transfers (CEI pattern)

### 1.3 Data Flow

```
Community submits extraction → ExtractionTracker.recordExtraction()
Oracle bridge submits data → MiningOracle.submitData() → consensus → verify
Oracle verifies → ExtractionTracker.verifyExtraction() → community confirms
Revenue arrives → RoyaltyDistributor.distributeRevenue() → 70/20/10 split
Token holders → QuadraticVoting.castVote() → governance decisions
```

---

## 2. Security Vulnerabilities

### 2.1 Critical Severity

#### C-1: `ExtractionTracker.setTokenURI()` — No Access Control (Anyone Can Modify Token URIs)

**File:** `ExtractionTracker.sol`  
**Lines:** `recordExtraction()` calls `setTokenURI()`

OpenZeppelin's `ERC721URIStorage.setTokenURI()` (v4.x, confirmed by the `_beforeTokenTransfer` signature with `batchSize` parameter) has **no access control**. Since ExtractionTracker inherits it publicly, anyone can call `setTokenURI(tokenId, "malicious")` on any minted soulbound NFT, overwriting the IPFS metadata URI with arbitrary data.

**Impact:** Critical data integrity violation. Extraction records — meant to be immutable proof — can have their metadata silently corrupted. The on-chain record data (`records` mapping) is unaffected, but the NFT metadata (which is the user-facing representation) is compromised.

**Recommendation:** Override `setTokenURI` with access control:
```solidity
function setTokenURI(uint256 tokenId, string memory _tokenURI) public override onlyRole(TRACKER_ADMIN) {
    super.setTokenURI(tokenId, _tokenURI);
}
```

#### C-2: `MiningOracle.submitData()` — No Duplicate Oracle Prevention (Single Oracle Can Trigger Consensus)

**File:** `MiningOracle.sol`  
**Lines:** `submitData()`

There is no check preventing the same oracle from submitting multiple times for the same `locationHash`. A single oracle with `ORACLE_ROLE` can submit `requiredConfirmations` times, bypassing the entire multi-oracle consensus mechanism.

```solidity
// No check: require(submissions[locationHash].length == 0 || submissions[locationHash][^].oracle != msg.sender)
```

**Impact:** Complete bypass of the consensus mechanism. A compromised single oracle can verify any location as legitimate.

**Recommendation:** Add per-oracle-per-location tracking:
```solidity
mapping(bytes32 => mapping(address => bool)) public hasSubmitted;

function submitData(...) external onlyRole(ORACLE_ROLE) {
    require(!hasSubmitted[locationHash][msg.sender], "Already submitted");
    hasSubmitted[locationHash][msg.sender] = true;
    // ...
}
```

### 2.2 High Severity

#### H-1: `ExtractionTracker.disputeExtraction()` — No Access Control (Anyone Can Dispute Any Record)

**File:** `ExtractionTracker.sol`  
**Lines:** `disputeExtraction()`

Anyone can dispute any record, including already-confirmed records. There's no:
- Token stake requirement
- Role check
- Prevention of disputing already-disputed records
- Prevention of disputing confirmed records

**Impact:** Griefing attack. An attacker can dispute every confirmed extraction record, inflating `disputedRecords` and undermining the verification system.

**Recommendation:** Add access control and state checks:
```solidity
function disputeExtraction(uint256 recordId, string calldata reason) external {
    ExtractionRecord storage record = records[recordId];
    require(record.submitter != address(0), "Record does not exist");
    require(record.status != VerificationStatus.DISPUTED, "Already disputed");
    require(record.status != VerificationStatus.COMMUNITY_CONFIRMED, "Cannot dispute confirmed");
    // Optionally require VERIFIER_ROLE or a token stake
    // ...
}
```

#### H-2: `ExtractionTracker.verifyExtraction()` — Can Re-Verify Already Verified Records

**File:** `ExtractionTracker.sol`  
**Lines:** `verifyExtraction()`

No check prevents verifying a record that's already `ORACLE_VERIFIED` or `COMMUNITY_CONFIRMED`. Each verification increments `verifiedRecords`, causing stat inflation.

```solidity
// Missing: require(record.status == VerificationStatus.UNVERIFIED, "Already processed");
```

**Impact:** `verifiedRecords` counter becomes inaccurate. An oracle could repeatedly verify the same record.

#### H-3: `RoyaltyDistributor.updateDestinations()` — Zero Address Not Validated

**File:** `RoyaltyDistributor.sol`  
**Lines:** `updateDestinations()`, `initialize()`

Neither `initialize()` nor `updateDestinations()` validate that destination addresses are not `address(0)`. If set to zero address, ETH sent via `distributeRevenue()` would be permanently burned.

```solidity
// Missing in both functions:
require(_devFund != address(0), "Invalid address");
```

**Impact:** Permanent loss of ETH if destination is set to zero address.

#### H-4: `GovernanceToken.createVesting()` — No Validation on Vesting Parameters

**File:** `GovernanceToken.sol`  
**Lines:** `createVesting()`

No validation that:
- `vestingDuration > 0` (would cause division by zero in `_calculateReleasable`)
- `vestingDuration >= cliffDuration` (if cliff > duration, tokens unlock fully at cliff)
- `amount > 0`
- `beneficiary != address(0)`

```solidity
// Division by zero if vestingDuration == 0:
uint256 vested = (schedule.totalAmount * elapsed) / schedule.vestingDuration;
```

**Impact:** Potential division by zero revert, permanently locking vested tokens.

### 2.3 Medium Severity

#### M-1: `GovernanceToken` — No `revokeVesting()` Despite `revocable` Field

**File:** `GovernanceToken.sol`

The `VestingSchedule` struct has a `revocable` field, but there's no `revokeVesting()` function. This is dead code that suggests an incomplete feature.

**Impact:** If a team member leaves or acts maliciously, their vesting cannot be revoked as the struct suggests it should be.

#### M-2: `MiningOracle.requiredConfirmations` — Can Be Set to 1 (Single Oracle)

**File:** `MiningOracle.sol`  
**Lines:** `setRequiredConfirmations()`

The admin can set `requiredConfirmations` to 1, effectively making the system single-oracle with no consensus. Combined with C-2, this is especially dangerous.

**Recommendation:** Add a minimum threshold: `require(_required >= 2, "Minimum 2 confirmations");`

#### M-3: `QuadraticVoting` — No Proposal Lifecycle Management

**File:** `QuadraticVoting.sol`

There's no concept of proposal creation, expiration, or execution. Anyone can vote on any `proposalId` (including non-existent ones). There's no way to:
- Cancel or modify a vote
- Set a voting period
- Link votes to actual executable proposals
- Prevent voting on already-finalized proposals

**Impact:** The contract is a voting mechanism without governance integration. Tokens can be locked voting on meaningless proposal IDs.

#### M-4: `ExtractionTracker.recordExtraction()` — No Spam Prevention

**File:** `ExtractionTracker.sol`

Anyone can mint unlimited soulbound NFTs with no cost beyond gas. An attacker could spam the contract with thousands of fake extraction records, bloating storage and making the system unusable.

**Recommendation:** Require a minimum token stake, a fee, or restrict to authorized submitters.

#### M-5: `RoyaltyDistributor.distributeRevenue()` — Destination Contract Can Block All Distributions

**File:** `RoyaltyDistributor.sol`

If any destination address is a contract that reverts on `receive()` (or consumes all gas), the entire `distributeRevenue()` call fails. The `require(devOk)` pattern means one bad destination blocks all revenue distribution.

**Recommendation:** Use try/catch or allow individual withdrawal:
```solidity
(bool devOk, ) = communityDevelopmentFund.call{value: devShare}("");
if (!devOk) { pendingWithdrawals[communityDevelopmentFund] += devShare; }
```

### 2.4 Low Severity

#### L-1: `GovernanceToken` — No Event Emitted for Vesting Schedule Creation Details

The `TokensVested` event is emitted but doesn't include `revocable` flag or `vestingDuration` directly (only cliffEnd and vestingEnd timestamps). Off-chain indexers need to compute these.

#### L-2: `MiningOracle.activeOracles` — Never Used for Access Control

`activeOracles` mapping is set but never checked. It's purely informational.

#### L-3: `ExtractionTracker` — No `burn()` Function for Soulbound NFTs

Soulbound NFTs typically allow the owner to burn (dispose of) their token. Currently, there's no burn function, so the submitter is permanently linked to the record even if they want to disassociate.

#### L-4: `QuadraticVoting._sqrt()` — Potential Precision Loss for Very Large Numbers

The Babylonian method is correct, but for extremely large token amounts (approaching `uint256.max / 1e18`), the multiplication `tokens * PRECISION` in `castVote` could overflow. Solidity 0.8.20's overflow protection would revert, but this could be confusing.

#### L-5: Hardhat Config — Mumbai Testnet Deprecated

`hardhat.config.js` references Polygon Mumbai (chainId 80001), which was sunset in April 2024. Should be updated to Polygon Amoy (chainId 80002) or another active testnet.

---

## 3. Gas Optimization Opportunities

### 3.1 Storage Packing

#### `ExtractionTracker.ExtractionRecord` — Poor Packing

```solidity
struct ExtractionRecord {
    bytes32 locationHash;        // slot 0 (32 bytes)
    string mineralType;          // slot 1 (pointer)
    uint256 estimatedGradeBps;   // slot 2
    uint256 estimatedValueKES;   // slot 3
    uint256 confidenceScore;     // slot 4
    uint256 timestamp;           // slot 5
    address submitter;           // slot 6 (20 bytes + 12 wasted)
    VerificationStatus status;   // slot 7 (1 byte + 31 wasted)
    uint256 oracleTimestamp;     // slot 8
    address oracle;              // slot 9 (20 bytes + 12 wasted)
    string ipfsMetadataURI;      // slot 10 (pointer)
    string notes;                // slot 11 (pointer)
}
```

**Optimization:** Pack `submitter`, `status`, and `oracle` together:
```solidity
struct ExtractionRecord {
    bytes32 locationHash;        // slot 0
    uint256 estimatedGradeBps;   // slot 1
    uint256 estimatedValueKES;   // slot 2
    uint256 confidenceScore;     // slot 3
    uint256 timestamp;           // slot 4
    uint256 oracleTimestamp;     // slot 5
    address submitter;           // slot 6 (20 bytes)
    address oracle;              // slot 6 (20 bytes) — packed!
    VerificationStatus status;   // slot 7 (1 byte)
    // strings as pointers
}
```

Saves ~3 storage slots per record (~60,000 gas per mint).

#### `QuadraticVoting.Vote` — Redundant Fields

```solidity
struct Vote {
    uint256 proposalId;      // Already the mapping key
    address voter;           // Already the mapping key
    uint256 tokensCommitted; // slot
    uint256 quadraticPower;  // slot
    bool support;            // slot (1 byte, 31 wasted)
    uint256 timestamp;       // slot
}
```

`proposalId` and `voter` are redundant since they're mapping keys. Removing them saves 2 slots per vote.

### 3.2 String Storage

`ExtractionRecord` stores three strings on-chain (`mineralType`, `ipfsMetadataURI`, `notes`). Each string costs ~20,000 gas for SSTORE plus per-character costs. For a record with 5 strings of average 20 chars each, this is ~100,000+ gas just for string storage.

**Recommendation:** Store only hashes or IPFS CIDs on-chain; keep full metadata off-chain.

### 3.3 Unbounded Loops

`MiningOracle._verifyLocation()` iterates over all submissions for a location. If many oracles submit before consensus, this could hit gas limits. Consider a running average or incremental tracking.

`ExtractionTracker.getLocationRecords()` returns an unbounded array. For popular locations, this could exceed gas limits on view calls.

### 3.4 Redundant State Updates

In `QuadraticVoting.withdrawVote()`, the vote data is deleted but `totalForPower`/`totalAgainstPower` are not updated. If this is intentional (immutable vote results), the `Vote` struct could omit fields that are never read after withdrawal.

### 3.5 Missing `unchecked` Blocks

Safe arithmetic that's already protected by prior checks could use `unchecked` to save gas:
```solidity
// In _calculateReleasable, after checking elapsed >= vestingDuration:
unchecked {
    uint256 vested = (schedule.totalAmount * elapsed) / schedule.vestingDuration;
    return vested - schedule.released;
}
```

---

## 4. Test Coverage Assessment

### 4.1 Coverage Summary

| Contract | Test File | Test Count | Coverage |
|----------|-----------|------------|----------|
| GovernanceToken | ❌ **MISSING** | 0 | **None** |
| ExtractionTracker | `ExtractionTracker.test.js` | ~25 | Good |
| MiningOracle | `MiningOracle.test.js` | ~25 | Good |
| QuadraticVoting | `QuadraticVoting.test.js` | ~25 | Excellent |
| RoyaltyDistributor | `RoyaltyDistributor.test.js` | ~20 | Good |

### 4.2 Critical Test Gaps

1. **No GovernanceToken tests at all.** Vesting logic, release calculations, cliff behavior, and MAX_SUPPLY enforcement are completely untested.

2. **No test for duplicate oracle submissions** (C-2). The MiningOracle tests don't verify that the same oracle can't submit twice.

3. **No test for `setTokenURI` access control** (C-1). The ExtractionTracker tests verify `tokenURI` is set but don't test that unauthorized users can overwrite it.

4. **No test for dispute of already-disputed or confirmed records** (H-1). The dispute tests only cover the happy path.

5. **No test for re-verification of already-verified records** (H-2).

6. **No test for zero-address destinations** (H-3).

7. **No test for division by zero in vesting** (H-4).

8. **No fuzz testing or invariant testing.** All tests use specific values. Property-based testing would catch edge cases.

9. **No test for RoyaltyDistributor upgrade path.** Despite being UUPS, there's no test verifying the proxy can be upgraded safely.

10. **No test for RoyaltyDistributor receiving ETH via `receive()`.** The contract has no `receive()` function, so direct ETH transfers would revert — this should be tested.

### 4.3 Test Quality Issues

- `RoyaltyDistributor.test.js` line: `payer.sendTransaction({to: ..., value: amount})` — this sends ETH directly to the proxy without calling `distributeRevenue()`. Since there's no `receive()` function, this would revert. The test may be passing because of how Hardhat handles this, but it's not testing the intended flow.

- `QuadraticVoting.test.js` — Uses a real `GovernanceToken` instead of a mock. While this works, it couples the test to GovernanceToken's behavior. If GovernanceToken has a bug, QuadraticVoting tests would also fail.

---

## 5. Deployment Readiness

### 5.1 Deployment Script Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| Placeholder addresses | **Critical** | `devFund`, `communityWallet`, `reserve` all set to `deployer.address` |
| No role granting | **High** | ORACLE_ROLE, VERIFIER_ROLE never granted post-deployment |
| No verification | **Medium** | Contract source not verified on Polygonscan |
| No upgrade test | **Medium** | RoyaltyDistributor UUPS proxy not tested for upgradeability |
| Mumbai testnet | **High** | Mumbai is deprecated; config references dead network |
| No multisig | **High** | All admin roles granted to deployer EOA, not a multisig |

### 5.2 Missing Deployment Steps

1. **Grant ORACLE_ROLE** to oracle bridge addresses on MiningOracle
2. **Grant ORACLE_ROLE** to oracle bridge on ExtractionTracker
3. **Grant VERIFIER_ROLE** to community multisig on ExtractionTracker
4. **Grant MINTER_ROLE** to vesting/admin contracts on GovernanceToken
5. **Transfer DEFAULT_ADMIN_ROLE** to multisig/timelock
6. **Create initial vesting schedules** for all allocation buckets
7. **Set required confirmations** on MiningOracle to appropriate value
8. **Verify contracts** on Polygonscan
9. **Test upgrade path** for RoyaltyDistributor

### 5.3 Environment Variables Required

```
DEPLOYER_PRIVATE_KEY=    # Private key for deployment
MUMBAI_RPC_URL=          # Testnet RPC (deprecated)
POLYGON_RPC_URL=         # Mainnet RPC
POLYGONSCAN_API_KEY=     # For contract verification
```

⚠️ The deploy script accesses `process.env.DEPLOYER_PRIVATE_KEY` — ensure this is never committed to version control.

---

## 6. Code Quality & Best Practices

### 6.1 Strengths

- ✅ **Solidity 0.8.20** — Built-in overflow/underflow protection
- ✅ **OpenZeppelin libraries** — Battle-tested implementations for ERC20, ERC721, AccessControl, ReentrancyGuard
- ✅ **NatSpec documentation** — All contracts have detailed `@title`, `@notice`, `@dev` comments
- ✅ **Consistent naming** — Constants use UPPER_CASE, functions use camelCase
- ✅ **Event emissions** — All state changes emit events for off-chain indexing
- ✅ **CEI pattern** — Checks-Effects-Interactions followed in most functions
- ✅ **Immutable keyword** — `governanceToken` in QuadraticVoting is `immutable`
- ✅ **UUPS authorization** — `_authorizeUpgrade` properly gated to DAO_ROLE

### 6.2 Issues

- ⚠️ **Inconsistent error handling** — Some functions use `require` with messages, others rely on OpenZeppelin's built-in checks. No custom errors used (would save gas).
- ⚠️ **No emergency pause** — No `Pausable` pattern for critical functions. If a vulnerability is discovered, there's no way to halt the system.
- ⚠️ **No timelock** — Admin functions like `setRequiredConfirmations` and `updateSplits` take effect immediately. Should use OpenZeppelin's `TimelockController`.
- ⚠️ **Dead code** — `GovernanceToken.VestingSchedule.revocable` field is stored but never used.
- ⚠️ **No input validation** — Several functions lack parameter validation (see H-3, H-4).
- ⚠️ **Mixed proxy patterns** — Only RoyaltyDistributor is upgradeable. If a bug is found in ExtractionTracker or MiningOracle, there's no upgrade path.
- ⚠️ **No events for some state changes** — `ExtractionTracker.communityConfirm()` doesn't emit an event.

### 6.3 Code Smells

1. **God struct** — `ExtractionRecord` has 12 fields, suggesting it should be split or simplified
2. **Magic numbers** — `100 * PRECISION` in `hasProposalPassed` should be a named constant (`MINIMUM_QUORUM`)
3. **Unused imports** — `RoyaltyDistributor` imports `ReentrancyGuard` from `@openzeppelin/contracts` but also uses `__ReentrancyGuard_init()` from the upgradeable version. Need to verify which one is actually used.

---

## 7. Summary & Prioritized Recommendations

### Critical (Fix Before Deployment)

| # | Issue | Contract | Fix |
|---|-------|----------|-----|
| C-1 | `setTokenURI` has no access control | ExtractionTracker | Override with `onlyRole(TRACKER_ADMIN)` |
| C-2 | Single oracle can bypass consensus | MiningOracle | Add per-oracle-per-location duplicate check |

### High (Fix Before Deployment)

| # | Issue | Contract | Fix |
|---|-------|----------|-----|
| H-1 | `disputeExtraction` has no access control | ExtractionTracker | Add role check + state validation |
| H-2 | Can re-verify already-verified records | ExtractionTracker | Add `require(status == UNVERIFIED)` |
| H-3 | Zero-address destination not validated | RoyaltyDistributor | Add `require(addr != address(0))` |
| H-4 | Division by zero in vesting | GovernanceToken | Validate `vestingDuration > 0` |

### Medium (Fix Soon)

| # | Issue | Contract | Fix |
|---|-------|----------|-----|
| M-1 | `revocable` field unused | GovernanceToken | Implement `revokeVesting()` |
| M-2 | `requiredConfirmations` can be 1 | MiningOracle | Add minimum of 2 |
| M-3 | No proposal lifecycle | QuadraticVoting | Add proposal creation/expiry |
| M-4 | No spam prevention | ExtractionTracker | Require stake or fee |
| M-5 | Bad destination blocks all distributions | RoyaltyDistributor | Use try/catch with pending withdrawals |

### Deployment Checklist

- [ ] Write GovernanceToken tests
- [ ] Fix all Critical and High issues
- [ ] Update Mumbai → Amoy in hardhat config
- [ ] Replace placeholder addresses with real multisig
- [ ] Add role granting to deploy script
- [ ] Add contract verification to deploy script
- [ ] Test RoyaltyDistributor upgrade path
- [ ] Deploy multisig/timelock before deploying DAO contracts
- [ ] Consider adding `Pausable` to critical contracts
- [ ] Run Slither/Mythril static analysis
- [ ] Consider professional audit before mainnet

---

## 8. Overall Assessment

| Category | Rating | Notes |
|----------|--------|-------|
| Architecture | ⭐⭐⭐⭐ | Well-structured, clear separation of concerns |
| Security | ⭐⭐ | Multiple critical/high issues need fixing |
| Gas Optimization | ⭐⭐⭐ | Moderate opportunities, not critical |
| Test Coverage | ⭐⭐⭐ | Good for 4/5 contracts, missing GovernanceToken entirely |
| Deployment Readiness | ⭐⭐ | Script exists but needs significant work |
| Code Quality | ⭐⭐⭐⭐ | Clean, well-documented, follows most best practices |

**Bottom Line:** The architecture is solid and the design patterns are appropriate for the use case. However, there are **2 critical and 4 high severity security issues** that must be addressed before deployment. The most dangerous are the uncontrolled `setTokenURI` (data integrity), the single-oracle consensus bypass (trust model), and the uncontrolled dispute function (governance attack surface). The missing GovernanceToken test suite is also a significant risk. With these fixes, this would be a well-designed DAO system.
