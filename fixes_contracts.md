# Smart Contract Security Fixes — Sovereign Resource DAO

**Date:** 2026-08-04  
**Status:** ✅ All fixes applied

---

## Critical Fixes

### C-1: ExtractionTracker.sol — `setTokenURI()` No Access Control
**Issue:** `setTokenURI()` was publicly callable by anyone, allowing metadata tampering on soulbound extraction records.  
**Fix:** Added an `override` of `setTokenURI()` with `onlyRole(TRACKER_ADMIN)` modifier that delegates to `super.setTokenURI()`.  
**File:** `ExtractionTracker.sol` (line ~204)

### C-2: MiningOracle.sol — Single Oracle Can Bypass Consensus
**Issue:** A single oracle address could submit multiple times for the same location, faking consensus.  
**Fix:** Added `mapping(bytes32 => mapping(address => bool)) public hasSubmitted` and a `require(!hasSubmitted[locationHash][msg.sender])` guard in `submitData()`. The flag is set to `true` after each submission.  
**File:** `MiningOracle.sol` (lines ~39, ~72-73)

---

## High Fixes

### H-1: ExtractionTracker.sol — `disputeExtraction()` No Access Control
**Issue:** Anyone could dispute any record without authorization, and already-disputed records could be re-disputed (counter inflation).  
**Fix:** Added `onlyRole(VERIFIER_ROLE)` modifier and `require(record.status != VerificationStatus.DISPUTED)` state check.  
**File:** `ExtractionTracker.sol` (line ~167)

### H-2: ExtractionTracker.sol — `verifyExtraction()` Can Re-verify
**Issue:** Oracle could re-verify already-processed records, inflating `verifiedRecords`/`disputedRecords` counters.  
**Fix:** Added `require(record.status == VerificationStatus.UNVERIFIED, "Already processed")` at the start of `verifyExtraction()`.  
**File:** `ExtractionTracker.sol` (line ~137)

### H-3: RoyaltyDistributor.sol — Zero Address Validation
**Issue:** `initialize()` and `updateDestinations()` accepted `address(0)` destinations, which would permanently lock funds.  
**Fix:** Added `require(addr != address(0))` checks in `initialize()` for all three destination addresses. Added redundant but explicit zero-checks in `updateDestinations()`.  
**File:** `RoyaltyDistributor.sol` (lines ~98-100, ~177-187)

### H-4: GovernanceToken.sol — Division by Zero in Vesting
**Issue:** `createVesting()` accepted `vestingDuration = 0`, causing division-by-zero in `_calculateReleasable()`. Also no validation on cliff vs. vesting duration or zero-amount/beneficiary.  
**Fix:** Added four `require` checks: `beneficiary != address(0)`, `amount > 0`, `vestingDuration > 0`, `vestingDuration >= cliffDuration`.  
**File:** `GovernanceToken.sol` (lines ~90-93)

---

## Medium Fixes

### M-2: MiningOracle.sol — `setRequiredConfirmations` Minimum Too Low
**Issue:** Admin could set required confirmations to 1, defeating the purpose of multi-oracle consensus.  
**Fix:** Changed minimum from `>= 1` to `>= 2`.  
**File:** `MiningOracle.sol` (line ~143)

### M-5: RoyaltyDistributor.sol — Bad Destination Blocks All Distributions
**Issue:** If any destination wallet's `call` reverted (e.g., contract that rejects ETH), the entire `distributeRevenue()` reverted, blocking all revenue distribution.  
**Fix:** Reverted the atomic all-or-nothing pattern. Failed transfers now accumulate in `mapping(address => uint256) public pendingWithdrawals`. Added `withdrawPending()` function so destinations can claim later (e.g., after fixing their contract).  
**File:** `RoyaltyDistributor.sol` (lines ~56, ~129-145, ~212-217)

---

## Files Modified

| File | Fixes Applied |
|------|---------------|
| `ExtractionTracker.sol` | C-1, H-1, H-2 |
| `MiningOracle.sol` | C-2, M-2 |
| `RoyaltyDistributor.sol` | H-3, M-5 |
| `GovernanceToken.sol` | H-4 |

## Not Modified

- `QuadraticVoting.sol` — No issues identified in the audit scope.
