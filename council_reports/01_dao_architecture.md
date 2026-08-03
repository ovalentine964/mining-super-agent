# Council Report 01: DAO Architecture & Blockchain Integration
## Mining Super-Agent → Sovereign Resource DAO Transformation

**Council:** COUNCIL 1 — DAO Architecture and Blockchain Integration
**Date:** 2026-08-03
**Status:** COMPLETE
**Scope:** Full codebase analysis at `mining-super-agent/`

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Existing Architecture Assessment](#2-existing-architecture-assessment)
3. [Smart Contract Architecture — Royalty Distribution](#3-smart-contract-architecture--royalty-distribution)
4. [DAO Governance Model — Quadratic Voting](#4-dao-governance-model--quadratic-voting)
5. [Blockchain Integration Layer](#5-blockchain-integration-layer)
6. [Gap Analysis: Current Code vs DAO Requirements](#6-gap-analysis-current-code-vs-dao-requirements)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Recommended File Structure](#8-recommended-file-structure)
9. [Risk Assessment](#9-risk-assessment)

---

## 1. EXECUTIVE SUMMARY

The existing Mining Super-Agent is a well-architected Python/FastAPI/Rust system designed to serve Kenyan miners with AI-powered geological intelligence. It uses a centralized architecture: PostgreSQL for data, a single-agent LLM pipeline, and user accounts managed via JWT/MFA.

**To transform this into a Sovereign Resource DAO, the following fundamental changes are required:**

| Dimension | Current State | DAO Target State |
|-----------|--------------|------------------|
| **Ownership** | Single developer/org | Community-owned via token governance |
| **Revenue** | No revenue mechanism | 70/20/10 royalty split on-chain |
| **Governance** | Centralized admin (`is_admin` flag) | Quadratic voting, on-chain proposals |
| **Data Trust** | PostgreSQL (trusted by users) | Blockchain-verified extraction records |
| **Identity** | Username/password/MFA | Wallet-based (Ethereum/Polygon) |
| **Operation** | Permissioned (admin-controlled) | Permissionless (smart contract-enforced) |
| **Financial** | NPV calculator (advisory) | Automatic royalty distribution |

**Chain Recommendation:** Polygon PoS (low gas, EVM-compatible, strong ecosystem for DAO tooling, existing presence in Kenya via Kotani Pay and other African crypto infrastructure).

---

## 2. EXISTING ARCHITECTURE ASSESSMENT

### 2.1 Current Stack Inventory

| Component | Technology | File Path | DAO Relevance |
|-----------|-----------|-----------|---------------|
| API Server | FastAPI (Python) | `mining-super-agent/src/api/main.py` | Becomes off-chain indexer + API gateway |
| Super-Agent | Single LLM + function calling | `mining-super-agent/src/superagent.py` | Continues as oracle data source |
| Tool Registry | YAML-driven, rate-limited, cached | `mining-super-agent/src/tools/registry.py` | Tools feed data to blockchain oracles |
| Database | PostgreSQL + PostGIS | `mining-super-agent/src/db/models.py` | Becomes off-chain index; core state moves on-chain |
| Rust Gateway | Actix-Web API + Redis caching | `mining-super-agent/rust/src/tools/` | High-perf indexer for chain events |
| Flutter App | Dart, offline-first | `mining-super-agent/flutter_app/` | Needs wallet integration (web3) |
| Auth | JWT + MFA + API keys | `mining-super-agent/src/api/routes/auth.py` | Replaced by wallet signature auth |
| Financial Tools | NPV/IRR calculations | `mining-super-agent/src/tools/financial.py` | Feeds royalty calculation oracles |
| Observations | User-submitted mineral data | `mining-super-agent/src/db/models.py:Observation` | Core data for extraction tracking NFTs |

### 2.2 Key Architectural Assets to Preserve

1. **Tool Registry** (`src/tools/registry.py`) — Excellent abstraction. Tools are already pluggable with rate limiting, caching, fallback chains. This becomes the oracle data pipeline.

2. **Geological Database** (`src/db/models.py`) — PostGIS schema with `mineral_occurrences`, `observations`, `geological_units` is well-designed. Becomes the off-chain index that mirrors on-chain extraction records.

3. **Financial Tools** (`src/tools/financial.py`) — NPV/IRR calculations with conservative assumptions. These feed the royalty distribution oracle.

4. **Market Data Chain** (`src/tools/market.py`) — Multi-provider fallback (yfinance → Finnhub → Alpha Vantage). Essential for real-time royalty valuation.

5. **Rust Gateway** (`rust/`) — High-performance service with Redis caching. Becomes the blockchain event indexer.

---

## 3. SMART CONTRACT ARCHITECTURE — ROYALTY DISTRIBUTION

### 3.1 Contract Overview

The royalty system extracts value from three revenue sources:
1. **Data licensing** — Institutions paying for aggregated mineral intelligence
2. **Extraction royalties** — Mining operations paying community royalties
3. **Platform fees** — Transaction fees on the DAO marketplace

All revenue flows through a single `RoyaltyDistributor` contract that enforces the 70/20/10 split immutably.

### 3.2 Core Contracts

```
contracts/
├── MiningDAO.sol              # Main DAO contract (governance + treasury)
├── RoyaltyDistributor.sol     # Automatic 70/20/10 split
├── ExtractionTracker.sol      # On-chain extraction verification NFTs
├── MineralIntelligence.sol    # Data licensing & access control
├── GovernanceToken.sol        # $MINE ERC-20 governance token
├── QuadraticVoting.sol        # Voting mechanism
├── ProposalManager.sol        # Proposal lifecycle
└── interfaces/
    ├── IRoyaltyDistributor.sol
    ├── IExtractionTracker.sol
    └── IMineralIntelligence.sol
```

### 3.3 RoyaltyDistributor.sol — Detailed Design

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title RoyaltyDistributor
 * @notice Automatically splits all incoming revenue:
 *         70% → Community Development Fund
 *         20% → Community Wallet (miners, data contributors)
 *         10% → Protocol Reserve (insurance, emergencies)
 *
 * @dev UUPS proxy pattern for upgradability (governance-gated).
 *      All splits are immutable in logic but percentages are
 *      adjustable via DAO vote (within bounds).
 */
contract RoyaltyDistributor is
    UUPSUpgradeable,
    AccessControlUpgradeable,
    ReentrancyGuard
{
    bytes32 public constant DISTRIBUTOR_ADMIN = keccak256("DISTRIBUTOR_ADMIN");
    bytes32 public constant DAO_ROLE = keccak256("DAO_ROLE");

    // Split percentages (basis points: 10000 = 100%)
    uint256 public communityDevelopmentBps = 7000; // 70%
    uint256 public communityWalletBps = 2000;      // 20%
    uint256 public reserveBps = 1000;               // 10%

    // Boundaries (cannot be changed even by DAO)
    uint256 public constant MIN_COMMUNITY_SHARE = 5000; // Min 50% to community
    uint256 public constant MAX_RESERVE_SHARE = 2000;   // Max 20% to reserve

    address public communityDevelopmentFund;
    address public communityWallet;
    address public protocolReserve;

    // Royalty sources
    enum RoyaltySource { DATA_LICENSING, EXTRACTION, PLATFORM_FEE, DONATION }

    uint256 public totalDistributed;
    uint256 public lastDistributionTimestamp;

    // Distribution event for off-chain indexing
    event RevenueDistributed(
        address indexed payer,
        RoyaltySource source,
        uint256 totalAmount,
        uint256 communityDevShare,
        uint256 communityWalletShare,
        uint256 reserveShare,
        uint256 timestamp
    );

    event SplitPercentagesUpdated(
        uint256 newDevBps,
        uint256 newWalletBps,
        uint256 newReserveBps,
        uint256 timestamp
    );

    /// @notice Receive and distribute revenue
    function distributeRevenue(RoyaltySource source) 
        external 
        payable 
        nonReentrant 
    {
        require(msg.value > 0, "Zero amount");

        uint256 devShare = (msg.value * communityDevelopmentBps) / 10000;
        uint256 walletShare = (msg.value * communityWalletBps) / 10000;
        uint256 reserveShare = msg.value - devShare - walletShare;

        totalDistributed += msg.value;
        lastDistributionTimestamp = block.timestamp;

        // Transfer shares
        (bool devOk, ) = communityDevelopmentFund.call{value: devShare}("");
        require(devOk, "Dev fund transfer failed");

        (bool walletOk, ) = communityWallet.call{value: walletShare}("");
        require(walletOk, "Community wallet transfer failed");

        (bool reserveOk, ) = protocolReserve.call{value: reserveShare}("");
        require(reserveOk, "Reserve transfer failed");

        emit RevenueDistributed(
            msg.sender, source, msg.value,
            devShare, walletShare, reserveShare, block.timestamp
        );
    }

    /// @notice Update split percentages (DAO-only, within bounds)
    function updateSplits(
        uint256 newDevBps,
        uint256 newWalletBps,
        uint256 newReserveBps
    ) external onlyRole(DAO_ROLE) {
        require(newDevBps + newWalletBps + newReserveBps == 10000, "Must sum to 100%");
        require(newDevBps + newWalletBps >= MIN_COMMUNITY_SHARE, "Community share too low");
        require(newReserveBps <= MAX_RESERVE_SHARE, "Reserve too high");

        communityDevelopmentBps = newDevBps;
        communityWalletBps = newWalletBps;
        reserveBps = newReserveBps;

        emit SplitPercentagesUpdated(newDevBps, newWalletBps, newReserveBps, block.timestamp);
    }

    // UUPS authorization
    function _authorizeUpgrade(address newImplementation)
        internal override onlyRole(DAO_ROLE) {}
}
```

### 3.4 ExtractionTracker.sol — Extraction Verification NFTs

Each verified mineral extraction event mints a non-transferable "Extraction Record NFT" (soulbound) containing:
- GPS coordinates (on-chain hash, full data on IPFS)
- Mineral type and estimated grade
- Timestamp and submitter wallet
- AI confidence score (from super-agent oracle)
- Verification status (unverified → oracle-verified → community-confirmed)

```solidity
contract ExtractionTracker is ERC721URIStorage, AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    enum VerificationStatus { UNVERIFIED, ORACLE_VERIFIED, COMMUNITY_CONFIRMED, DISPUTED }

    struct ExtractionRecord {
        bytes32 locationHash;        // keccak256(lat, lon)
        string mineralType;
        uint256 estimatedGradeBps;   // Grade in basis points
        uint256 confidenceScore;     // 0-10000 (basis points)
        uint256 timestamp;
        address submitter;
        VerificationStatus status;
        uint256 oracleTimestamp;
        address oracle;
        string ipfsMetadataURI;      // Full geological data
    }

    mapping(uint256 => ExtractionRecord) public records;
    uint256 public nextRecordId;

    event ExtractionRecorded(
        uint256 indexed recordId,
        address indexed submitter,
        bytes32 locationHash,
        string mineralType,
        VerificationStatus status
    );

    function recordExtraction(
        bytes32 locationHash,
        string calldata mineralType,
        uint256 estimatedGradeBps,
        uint256 confidenceScore,
        string calldata ipfsMetadataURI
    ) external returns (uint256) {
        uint256 recordId = nextRecordId++;

        records[recordId] = ExtractionRecord({
            locationHash: locationHash,
            mineralType: mineralType,
            estimatedGradeBps: estimatedGradeBps,
            confidenceScore: confidenceScore,
            timestamp: block.timestamp,
            submitter: msg.sender,
            status: VerificationStatus.UNVERIFIED,
            oracleTimestamp: 0,
            oracle: address(0),
            ipfsMetadataURI: ipfsMetadataURI
        });

        _safeMint(msg.sender, recordId);
        setTokenURI(recordId, ipfsMetadataURI);

        emit ExtractionRecorded(recordId, msg.sender, locationHash, mineralType, VerificationStatus.UNVERIFIED);
        return recordId;
    }

    function verifyExtraction(uint256 recordId, bool isValid) 
        external onlyRole(ORACLE_ROLE) 
    {
        ExtractionRecord storage record = records[recordId];
        record.status = isValid ? VerificationStatus.ORACLE_VERIFIED : VerificationStatus.DISPUTED;
        record.oracleTimestamp = block.timestamp;
        record.oracle = msg.sender;
    }
}
```

### 3.5 Revenue Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    REVENUE SOURCES                                │
├──────────────┬───────────────────┬───────────────────────────────┤
│ Data Licensing│ Extraction Royalty│ Platform Fees                 │
│ (Institutions)│ (Mining Ops)      │ (Marketplace transactions)    │
└──────┬───────┴───────┬───────────┴───────────┬───────────────────┘
       │               │                       │
       └───────────────┼───────────────────────┘
                       │
                       ▼
       ┌───────────────────────────────┐
       │    RoyaltyDistributor.sol     │
       │    (receive + split)          │
       └───────────┬───────────────────┘
                   │
       ┌───────────┼───────────────┐
       │           │               │
       ▼           ▼               ▼
┌──────────┐ ┌──────────┐  ┌──────────────┐
│ 70%      │ │ 20%      │  │ 10%          │
│ Community│ │ Community│  │ Protocol     │
│ Dev Fund │ │ Wallets  │  │ Reserve      │
├──────────┤ ├──────────┤  ├──────────────┤
│ • AI R&D │ │ • Miner  │  │ • Insurance  │
│ • Tools  │ │   rewards│  │ • Emergency  │
│ • Infra  │ │ • Data   │  │ • Audits     │
│ • Edu    │ │   bounties│ │ • Legal      │
└──────────┘ └──────────┘  └──────────────┘
```

---

## 4. DAO GOVERNANCE MODEL — QUADRATIC VOTING

### 4.1 Governance Token: $MINE (ERC-20)

**Token Utility:**
- Voting power in quadratic governance
- Staking for data access tiers
- Royalty claim eligibility (staked tokens receive proportional community wallet share)
- Oracle participation (stake required to run verification nodes)

**Token Distribution:**

| Allocation | Percentage | Vesting | Purpose |
|-----------|-----------|---------|---------|
| Community (miners) | 40% | 4-year linear, 1yr cliff | Airdrop to verified miners based on contribution |
| Data Contributors | 20% | 3-year linear | Rewards for submitting observations/geological data |
| Development Team | 15% | 4-year linear, 2yr cliff | Core contributors |
| DAO Treasury | 15% | Governed by proposals | Community-controlled reserves |
| Liquidity | 10% | No vesting | DEX liquidity (Uniswap/Quickswap) |

**Total Supply:** 1,000,000,000 $MINE

### 4.2 Quadratic Voting Mechanism

Standard quadratic voting: voting power = √(tokens staked for vote). This prevents plutocratic control while still rewarding larger stakeholders.

```solidity
contract QuadraticVoting is AccessControl, ReentrancyGuard {
    struct Vote {
        uint256 proposalId;
        address voter;
        uint256 tokensCommitted;      // Actual tokens locked
        uint256 quadraticPower;       // sqrt(tokensCommitted) * PRECISION
        bool support;                 // true = for, false = against
        uint256 timestamp;
    }

    uint256 public constant PRECISION = 1e18;
    uint256 public constant VOTE_LOCK_DURATION = 7 days;

    IERC20 public immutable governanceToken;

    mapping(uint256 => mapping(address => Vote)) public votes;
    mapping(uint256 => uint256) public totalForPower;
    mapping(uint256 => uint256) public totalAgainstPower;
    mapping(uint256 => uint256) public totalTokensLocked;

    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        uint256 tokensCommitted,
        uint256 quadraticPower,
        bool support
    );

    /// @notice Cast a quadratic vote
    /// @param proposalId The proposal to vote on
    /// @param tokens Amount of $MINE tokens to commit (locked for VOTE_LOCK_DURATION)
    /// @param support true = for, false = against
    function castVote(uint256 proposalId, uint256 tokens, bool support) 
        external nonReentrant 
    {
        require(tokens > 0, "Must commit tokens");

        // Lock tokens
        governanceToken.transferFrom(msg.sender, address(this), tokens);

        // Calculate quadratic power: sqrt(tokens) * PRECISION
        uint256 qPower = _sqrt(tokens * PRECISION);

        votes[proposalId][msg.sender] = Vote({
            proposalId: proposalId,
            voter: msg.sender,
            tokensCommitted: tokens,
            quadraticPower: qPower,
            support: support,
            timestamp: block.timestamp
        });

        if (support) {
            totalForPower[proposalId] += qPower;
        } else {
            totalAgainstPower[proposalId] += qPower;
        }
        totalTokensLocked[proposalId] += tokens;

        emit VoteCast(proposalId, msg.sender, tokens, qPower, support);
    }

    /// @notice Reclaim tokens after voting period ends
    function reclaimTokens(uint256 proposalId) external nonReentrant {
        Vote storage vote = votes[proposalId][msg.sender];
        require(vote.tokensCommitted > 0, "No vote found");
        // Check vote period ended (handled by ProposalManager)

        uint256 tokens = vote.tokensCommitted;
        vote.tokensCommitted = 0;
        totalTokensLocked[proposalId] -= tokens;

        governanceToken.transfer(msg.sender, tokens);
    }

    /// @dev Integer square root (Babylonian method)
    function _sqrt(uint256 x) internal pure returns (uint256 y) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }
}
```

### 4.3 Proposal Lifecycle

```solidity
contract ProposalManager is AccessControl, ReentrancyGuard {
    enum ProposalState { 
        PENDING,      // Created, not yet active
        ACTIVE,       // Voting period open
        PASSED,       // Quorum reached, majority for
        FAILED,       // Quorum not reached or majority against
        EXECUTED,     // Proposal executed
        CANCELLED,    // Cancelled by proposer or emergency
        VETOED        // Emergency multisig veto (security only)
    }

    enum ProposalType {
        PARAMETER_CHANGE,   // Change system parameters
        FUND_ALLOCATION,    // Treasury spending
        ROYALTY_UPDATE,     // Change royalty split percentages
        TOOL_ADDITION,      // Add new tool to the registry
        ORACLE_APPOINTMENT, // Approve a new oracle node
        CONSTITUTIONAL,     // Changes to governance rules themselves
        EMERGENCY           // Emergency actions (higher quorum)
    }

    struct Proposal {
        uint256 id;
        address proposer;
        ProposalType proposalType;
        string title;
        string description;      // IPFS hash of full proposal
        address targetContract;  // Contract to call
        bytes callData;          // Encoded function call
        uint256 value;           // ETH value (for treasury proposals)
        uint256 createdAt;
        uint256 votingStart;
        uint256 votingEnd;
        uint256 executionDeadline;
        ProposalState state;
        uint256 forVotes;        // Quadratic power
        uint256 againstVotes;    // Quadratic power
        uint256 totalTokensLocked;
        bool executed;
    }

    // Governance parameters
    uint256 public votingPeriod = 5 days;
    uint256 public executionDelay = 2 days;       // Timelock
    uint256 public quorumBps = 400;                // 4% of total supply
    uint256 public proposalThresholdBps = 100;     // 0.1% of supply to propose
    uint256 public emergencyQuorumBps = 1000;      // 10% for emergency proposals

    // Per-type quorum overrides
    mapping(ProposalType => uint256) public typeQuorumBps;

    mapping(uint256 => Proposal) public proposals;
    uint256 public nextProposalId;

    event ProposalCreated(uint256 indexed id, address proposer, ProposalType pType, string title);
    event ProposalExecuted(uint256 indexed id, bool success);
    event ProposalStateChanged(uint256 indexed id, ProposalState newState);

    /// @notice Create a proposal
    function propose(
        ProposalType pType,
        string calldata title,
        string calldata descriptionIPFS,
        address targetContract,
        bytes calldata callData,
        uint256 value
    ) external returns (uint256) {
        require(
            governanceToken.balanceOf(msg.sender) >= proposalThreshold(),
            "Below proposal threshold"
        );

        uint256 proposalId = nextProposalId++;

        proposals[proposalId] = Proposal({
            id: proposalId,
            proposer: msg.sender,
            proposalType: pType,
            title: title,
            description: descriptionIPFS,
            targetContract: targetContract,
            callData: callData,
            value: value,
            createdAt: block.timestamp,
            votingStart: block.timestamp + 1 days,  // 1 day delay
            votingEnd: block.timestamp + 1 days + votingPeriod,
            executionDeadline: block.timestamp + 1 days + votingPeriod + executionDelay,
            state: ProposalState.PENDING,
            forVotes: 0,
            againstVotes: 0,
            totalTokensLocked: 0,
            executed: false
        });

        emit ProposalCreated(proposalId, msg.sender, pType, title);
        return proposalId;
    }

    /// @notice Execute a passed proposal (after timelock)
    function executeProposal(uint256 proposalId) external nonReentrant {
        Proposal storage p = proposals[proposalId];
        require(p.state == ProposalState.PASSED, "Not passed");
        require(block.timestamp >= p.executionDeadline, "Timelock not expired");
        require(block.timestamp <= p.executionDeadline + 30 days, "Execution window closed");

        p.state = ProposalState.EXECUTED;
        p.executed = true;

        (bool success, ) = p.targetContract.call{value: p.value}(p.callData);

        emit ProposalExecuted(proposalId, success);
    }
}
```

### 4.4 Governance Safeguards

| Safeguard | Mechanism | Purpose |
|-----------|-----------|---------|
| **Timelock** | 2-day delay after pass before execution | Allows exit if malicious proposal passes |
| **Quorum floors** | Min 4% participation (10% for emergency) | Prevents low-participation attacks |
| **Proposal threshold** | 0.1% of supply to submit | Prevents spam |
| **Emergency multisig** | 5-of-9 multisig can veto | Security backstop for critical vulnerabilities |
| **Quadratic voting** | Power = √(tokens) | Prevents whale domination |
| **Vote lock** | 7-day token lock after voting | Prevents flash-loan governance attacks |
| **Constitutional proposals** | Higher quorum (8%) for governance changes | Protects core rules |
| **Split bounds** | Community share ≥ 50%, reserve ≤ 20% | Hard-coded economic protection |

---

## 5. BLOCKCHAIN INTEGRATION LAYER

### 5.1 Chain Selection: Polygon PoS

**Rationale:**

| Factor | Polygon PoS | Ethereum L1 | Arbitrum/Optimism | Solana |
|--------|------------|-------------|-------------------|--------|
| Gas cost | ~$0.001-0.01 | $1-50 | $0.01-0.10 | $0.001 |
| Finality | ~2s | ~12min | ~10min (L1) | ~0.4s |
| EVM compatible | ✅ | ✅ | ✅ | ❌ |
| DAO tooling | ✅ Excellent | ✅ Best | ✅ Good | ⚠️ Limited |
| African infra | ✅ Kotani Pay | ❌ | ❌ | ❌ |
| Decentralization | ⚠️ Medium | ✅ High | ⚠️ Medium | ⚠️ Medium |
| Bridge security | ✅ Good | N/A | ⚠️ Bridge risk | ❌ |

Polygon wins for this use case: low cost for frequent miner interactions, strong DAO tooling, existing African payment infrastructure, and EVM compatibility (can reuse Solidity contracts).

### 5.2 Oracle Architecture

The super-agent's tools become blockchain oracles that feed verified data on-chain.

```
┌─────────────────────────────────────────────────────────────┐
│                    OFF-CHAIN (Current Stack)                  │
│                                                              │
│  MiningSuperAgent ─→ ToolRegistry ─→ [Geological, Market,   │
│                        │               Satellite, Vision,    │
│                        │               Financial, Quantum]   │
│                        │                                     │
│                   Oracle Bridge                               │
│                   (Chainlink-style)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ON-CHAIN (Polygon)                         │
│                                                              │
│  MiningOracle.sol ←── Verified data submissions              │
│       │                                                      │
│       ├──→ ExtractionTracker.sol (extraction verification)   │
│       ├──→ RoyaltyDistributor.sol (revenue calculations)     │
│       └──→ MineralIntelligence.sol (data licensing)          │
└─────────────────────────────────────────────────────────────┘
```

#### MiningOracle.sol

```solidity
contract MiningOracle is AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");

    struct OracleSubmission {
        bytes32 locationHash;
        string mineralType;
        uint256 estimatedValueUSD;     // In cents (2 decimals)
        uint256 confidenceBps;         // 0-10000
        bytes32 dataHash;              // Hash of full geological data
        uint256 timestamp;
        address oracle;
        bool verified;
    }

    // Minimum 3 oracle confirmations for data to be considered verified
    uint256 public constant MIN_CONFIRMATIONS = 3;
    mapping(bytes32 => OracleSubmission[]) public submissions;
    mapping(bytes32 => mapping(address => bool)) public hasSubmitted;

    event OracleDataSubmitted(
        bytes32 indexed dataHash,
        address indexed oracle,
        bytes32 locationHash,
        string mineralType,
        uint256 confidenceBps
    );

    event DataVerified(
        bytes32 indexed dataHash,
        uint256 confirmationCount,
        uint256 aggregateConfidence
    );

    /// @notice Submit geological data from the super-agent tool chain
    function submitData(
        bytes32 locationHash,
        string calldata mineralType,
        uint256 estimatedValueUSD,
        uint256 confidenceBps,
        bytes32 dataHash
    ) external onlyRole(ORACLE_ROLE) {
        require(!hasSubmitted[dataHash][msg.sender], "Already submitted");

        submissions[dataHash].push(OracleSubmission({
            locationHash: locationHash,
            mineralType: mineralType,
            estimatedValueUSD: estimatedValueUSD,
            confidenceBps: confidenceBps,
            dataHash: dataHash,
            timestamp: block.timestamp,
            oracle: msg.sender,
            verified: false
        }));

        hasSubmitted[dataHash][msg.sender] = true;

        emit OracleDataSubmitted(dataHash, msg.sender, locationHash, mineralType, confidenceBps);

        // Auto-verify if enough confirmations
        if (submissions[dataHash].length >= MIN_CONFIRMATIONS) {
            _verifyData(dataHash);
        }
    }

    function _verifyData(bytes32 dataHash) internal {
        uint256 totalConfidence = 0;
        for (uint i = 0; i < submissions[dataHash].length; i++) {
            totalConfidence += submissions[dataHash][i].confidenceBps;
        }
        uint256 avgConfidence = totalConfidence / submissions[dataHash].length;

        emit DataVerified(dataHash, submissions[dataHash].length, avgConfidence);
    }
}
```

### 5.3 Oracle Bridge Implementation

The bridge between the Python/Rust off-chain system and the blockchain oracle is a dedicated service:

**New file: `mining-super-agent/src/chain/oracle_bridge.py`**

```python
"""
Oracle Bridge — Translates tool registry outputs into blockchain oracle submissions.

Listens for new verified observations in PostgreSQL, encodes them,
and submits to MiningOracle.sol via Polygon RPC.
"""

import asyncio
import hashlib
import json
import logging
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)


class OracleBridge:
    def __init__(self, rpc_url: str, oracle_key: str, oracle_address: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(oracle_key)
        self.oracle_address = oracle_address
        # Load contract ABI
        self.oracle_contract = self.w3.eth.contract(
            address=self.oracle_address,
            abi=self._load_abi("MiningOracle")
        )

    def _hash_observation(self, observation: dict) -> bytes:
        """Create deterministic hash of observation data."""
        canonical = json.dumps(observation, sort_keys=True).encode()
        return hashlib.sha256(canonical).digest()

    async def submit_observation(self, observation: dict) -> str:
        """Submit a verified observation to the blockchain oracle."""
        location_hash = Web3.solidity_keccak(
            ['uint256', 'uint256'],
            [int(observation['lat'] * 1e6), int(observation['lon'] * 1e6)]
        )
        data_hash = self._hash_observation(observation)

        tx = self.oracle_contract.functions.submitData(
            location_hash,
            observation['mineral_type'],
            int(observation['estimated_value_usd'] * 100),  # cents
            int(observation['confidence'] * 10000),          # basis points
            data_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(30, 'gwei'),
        })

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        logger.info(f"Oracle submission confirmed: {tx_hash.hex()}")
        return tx_hash.hex()
```

### 5.4 Identity & Wallet Integration

Replace JWT auth with wallet-based authentication:

**New file: `mining-super-agent/src/api/routes/wallet_auth.py`**

```python
"""
Wallet-based authentication — Sign-In With Ethereum (SIWE).

Users authenticate by signing a message with their wallet.
No passwords, no JWT secrets, no centralized identity provider.
"""

from siwe import SiweMessage
from eth_account import Account
from eth_account.messages import encode_defunct


async def verify_wallet_signature(message: str, signature: str) -> dict:
    """Verify a SIWE signature and return wallet address."""
    siwe = SiweMessage(message=message)
    # Validate the message (domain, nonce, expiration)
    verified = siwe.verify(signature)
    if not verified:
        raise ValueError("Invalid signature")
    return {"address": siwe.address, "chain_id": siwe.chain_id}
```

### 5.5 Flutter App Wallet Integration

The Flutter mobile app needs wallet connectivity. Using `walletconnect_flutter_v2` or `web3dart`:

**New dependency in `pubspec.yaml`:**
```yaml
dependencies:
  walletconnect_flutter_v2: ^2.3.1
  web3dart: ^2.7.3
  ethers: ^0.0.1  # or web3dart for signing
```

**New file: `flutter_app/lib/services/wallet_service.dart`**
```dart
// Wallet connection, SIWE signing, on-chain transaction submission
// Connects to MetaMask, Trust Wallet, or WalletConnect v2
```

---

## 6. GAP ANALYSIS: CURRENT CODE VS DAO REQUIREMENTS

### 6.1 Critical Gaps

| # | Gap | Current State | DAO Requirement | Priority | Effort |
|---|-----|--------------|-----------------|----------|--------|
| G1 | **No smart contracts** | Zero Solidity code | Full contract suite (8+ contracts) | CRITICAL | 6-8 weeks |
| G2 | **Centralized auth** | JWT + MFA + passwords | Wallet-based (SIWE) | CRITICAL | 2-3 weeks |
| G3 | **No token economics** | No token | $MINE ERC-20 with distribution | CRITICAL | 3-4 weeks |
| G4 | **Centralized data trust** | PostgreSQL (user trusts server) | Blockchain-verified extraction records | CRITICAL | 4-5 weeks |
| G5 | **No governance** | `is_admin` boolean flag | Quadratic voting, proposal system | HIGH | 4-5 weeks |
| G6 | **No royalty distribution** | NPV calculator (advisory only) | Automatic on-chain 70/20/10 split | HIGH | 3-4 weeks |
| G7 | **No oracle bridge** | Tools output to API only | Python → blockchain oracle pipeline | HIGH | 2-3 weeks |
| G8 | **No IPFS integration** | MinIO for file storage | IPFS for metadata, extraction records | MEDIUM | 1-2 weeks |
| G9 | **No on-chain governance params** | Config in YAML files | On-chain parameter management | MEDIUM | 2-3 weeks |
| G10 | **No DEX liquidity** | N/A | $MINE/USDC pool on QuickSwap | MEDIUM | 1 week |

### 6.2 Components That Need Modification

| File/Component | Change Required | Description |
|---------------|----------------|-------------|
| `src/api/routes/auth.py` | **Replace** | JWT auth → wallet signature auth (SIWE) |
| `src/config/settings.py` | **Extend** | Add Polygon RPC, contract addresses, oracle keys |
| `src/db/models.py` | **Extend** | Add `wallet_address` to User, `chain_tx_hash` to Observation |
| `src/tools/registry.py` | **Extend** | Add oracle submission hook after tool execution |
| `src/tools/financial.py` | **Extend** | Feed royalty calculations to oracle bridge |
| `src/superagent.py` | **Extend** | Wallet-aware user context, on-chain data references |
| `flutter_app/` | **Major changes** | Wallet connection, on-chain transactions, token staking |
| `docker-compose.yml` | **Extend** | Add Polygon node (or use Alchemy/Infura), IPFS node |
| `rust/src/tools/mod.rs` | **Extend** | Add blockchain event indexing endpoints |
| `rust/Cargo.toml` | **Extend** | Add `ethers-rs` for blockchain interaction |

### 6.3 Components to Preserve As-Is

| Component | Reason |
|-----------|--------|
| `src/tools/geological.py` | Oracle data source — no changes needed |
| `src/tools/market.py` | Oracle data source — no changes needed |
| `src/tools/satellite.py` | Oracle data source — no changes needed |
| `src/tools/quantum.py` | Oracle data source — no changes needed |
| `src/ml/*` | AI models for mineral classification — feeds oracle confidence scores |
| `src/config/agent.yaml` | Agent configuration — independent of blockchain layer |
| `src/reports/` | PDF generation — off-chain utility |

---

## 7. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Smart contracts deployed to Polygon Mumbai testnet, basic wallet auth working.

| Week | Deliverable | Files |
|------|------------|-------|
| 1 | Hardhat project setup, GovernanceToken.sol, RoyaltyDistributor.sol | `contracts/` |
| 2 | ExtractionTracker.sol, MiningOracle.sol, test suites | `contracts/test/` |
| 3 | Oracle bridge (Python → Polygon), wallet auth (SIWE) | `src/chain/oracle_bridge.py`, `src/api/routes/wallet_auth.py` |
| 4 | Flutter wallet integration (basic), Mumbai testnet deployment | `flutter_app/lib/services/wallet_service.dart` |

### Phase 2: Governance (Weeks 5-8)

**Goal:** Quadratic voting live, proposal system operational.

| Week | Deliverable | Files |
|------|------------|-------|
| 5 | QuadraticVoting.sol, ProposalManager.sol | `contracts/` |
| 6 | Governance frontend (React or Flutter), proposal creation | `src/api/routes/governance.py` |
| 7 | Token distribution contract, miner airdrop mechanism | `contracts/TokenDistributor.sol` |
| 8 | Governance integration testing, testnet full-flow | All governance files |

### Phase 3: Production (Weeks 9-12)

**Goal:** Mainnet deployment, token launch, first community distributions.

| Week | Deliverable | Files |
|------|------------|-------|
| 9 | Security audit (contracts), bug bounty program | External audit |
| 10 | Polygon mainnet deployment, contract verification | `contracts/deploy/` |
| 11 | Token generation event, DEX liquidity provision | On-chain |
| 12 | First royalty distribution, community wallet setup | Live system |

### Phase 4: Maturity (Weeks 13-16)

**Goal:** Full decentralization, community governance active.

| Week | Deliverable | Files |
|------|------------|-------|
| 13 | Oracle node decentralization (community oracles) | `contracts/OracleStaking.sol` |
| 14 | Cross-chain bridge consideration (Ethereum L1 for treasury) | Research |
| 15 | Data marketplace (mineral intelligence licensing) | `contracts/MineralIntelligence.sol` |
| 16 | Progressive decentralization — team multisig → full DAO | Governance transition |

---

## 8. RECOMMENDED FILE STRUCTURE

```
mining-super-agent/
├── contracts/                          # NEW — Smart contracts
│   ├── src/
│   │   ├── MiningDAO.sol
│   │   ├── RoyaltyDistributor.sol
│   │   ├── ExtractionTracker.sol
│   │   ├── GovernanceToken.sol
│   │   ├── QuadraticVoting.sol
│   │   ├── ProposalManager.sol
│   │   ├── MiningOracle.sol
│   │   ├── MineralIntelligence.sol
│   │   ├── OracleStaking.sol
│   │   └── interfaces/
│   │       ├── IRoyaltyDistributor.sol
│   │       ├── IExtractionTracker.sol
│   │       └── IMineralIntelligence.sol
│   ├── test/
│   │   ├── RoyaltyDistributor.t.sol
│   │   ├── ExtractionTracker.t.sol
│   │   ├── QuadraticVoting.t.sol
│   │   └── ProposalManager.t.sol
│   ├── script/
│   │   ├── DeployMumbai.s.sol
│   │   ├── DeployPolygon.s.sol
│   │   └── VerifyContracts.s.sol
│   ├── foundry.toml
│   └── remappings.txt
│
├── mining-super-agent/                 # EXISTING — Modified
│   ├── src/
│   │   ├── chain/                     # NEW — Blockchain integration
│   │   │   ├── __init__.py
│   │   │   ├── oracle_bridge.py       # Tool → Oracle submission
│   │   │   ├── contract_client.py     # Web3 contract interaction
│   │   │   ├── indexer.py             # Chain event indexer
│   │   │   └── config.py              # Chain configuration
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── wallet_auth.py     # NEW — SIWE authentication
│   │   │   │   ├── governance.py      # NEW — Proposal endpoints
│   │   │   │   ├── royalties.py       # NEW — Royalty tracking
│   │   │   │   ├── auth.py            # MODIFIED — Add wallet auth
│   │   │   │   └── ...                # Existing routes preserved
│   │   ├── config/
│   │   │   ├── settings.py            # MODIFIED — Add chain config
│   │   │   └── ...
│   │   ├── db/
│   │   │   ├── models.py              # MODIFIED — Add wallet fields
│   │   │   └── ...
│   │   ├── tools/
│   │   │   ├── registry.py            # MODIFIED — Oracle hook
│   │   │   └── ...                    # Existing tools preserved
│   │   └── ...                        # Existing code preserved
│   └── docker-compose.yml             # MODIFIED — Add chain services
│
└── flutter_app/                        # EXISTING — Major modifications
    ├── lib/
    │   ├── services/
    │   │   ├── wallet_service.dart     # NEW — Wallet connection
    │   │   ├── governance_service.dart # NEW — Voting UI
    │   │   └── ...
    │   ├── screens/
    │   │   ├── wallet_screen.dart      # NEW — Wallet management
    │   │   ├── governance_screen.dart  # NEW — Proposals & voting
    │   │   └── ...
    │   └── ...
    └── pubspec.yaml                    # MODIFIED — Add web3 deps
```

---

## 9. RISK ASSESSMENT

### 9.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Smart contract vulnerability | CRITICAL | Professional audit (Trail of Bits, OpenZeppelin), bug bounty, UUPS upgradeable pattern |
| Oracle manipulation (fake data) | HIGH | Multi-oracle consensus (min 3), staking/slashing, reputation system |
| Polygon network downtime | MEDIUM | Ethereum L1 fallback for treasury, multi-chain design ready |
| Gas price spikes | LOW | Polygon gas is negligible; batch transactions where possible |
| Flash loan governance attack | HIGH | 7-day vote lock, quadratic voting reduces leverage |
| Key management (oracle keys) | HIGH | Hardware security modules, key rotation, multisig oracles |

### 9.2 Regulatory Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Kenya CMA token classification | MEDIUM | Utility token (governance + access), not security; legal counsel required |
| DAO legal entity | MEDIUM | Wyoming DAO LLC or Marshall Islands; provides legal wrapper |
| KYC/AML for token distribution | MEDIUM | Tiered access; on-chain governance doesn't require KYC; fiat on/off ramps do |
| Mining license compliance | HIGH | DAO doesn't replace government licenses; it provides intelligence and fair revenue sharing |

### 9.3 Adoption Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Miners have no crypto wallets | HIGH | Flutter app includes simple wallet creation (account abstraction / smart wallets); Kotani Pay for mobile money → crypto bridge |
| Low governance participation | MEDIUM | Delegation mechanism, participation rewards, simple mobile-first UI |
| Language barriers | MEDIUM | Swahili-first UI (already built), Luo translations (already in Flutter l10n) |
| Internet connectivity | MEDIUM | Offline-first Flutter app (already built), sync when connected |

---

## APPENDIX A: CONTRACT INTERACTION DIAGRAM

```
User (Flutter App)
    │
    ├─── Wallet Connect (SIWE) ──────────────► wallet_auth.py
    │                                              │
    ├─── Submit Observation ──► superagent.py       │
    │                              │               │
    │                              ▼               │
    │                        ToolRegistry          │
    │                              │               │
    │                              ▼               │
    │                        OracleBridge ◄────────┘
    │                              │
    │                              ▼
    │                    MiningOracle.sol
    │                              │
    │                    ┌─────────┼──────────┐
    │                    ▼         ▼          ▼
    │          ExtractionTracker  Royalty   Governance
    │              .sol         Distributor  Token
    │                            .sol         .sol
    │                              │
    │                              ▼
    │                    Revenue Distribution
    │                    70% / 20% / 10%
    │
    ├─── Vote on Proposal ──► QuadraticVoting.sol
    │                              │
    │                              ▼
    │                    ProposalManager.sol
    │                              │
    │                              ▼
    │                    Execute via Timelock
    │
    └─── Track Extraction ──► ExtractionTracker.sol
                                  │
                                  ▼
                         Soulbound NFT Record
                         (on-chain + IPFS metadata)
```

---

## APPENDIX B: DEPENDENCY CHANGES

### Python (`requirements-bot.txt` additions)

```
web3>=6.15.0
eth-account>=0.11.0
siwe-py>=2.0.0
ipfshttpclient>=0.8.0
```

### Rust (`Cargo.toml` additions)

```toml
ethers = "2.0"
alloy = "0.1"  # Alternative modern Rust Ethereum library
```

### Flutter (`pubspec.yaml` additions)

```yaml
dependencies:
  walletconnect_flutter_v2: ^2.3.1
  web3dart: ^2.7.3
  bip39: ^1.0.6
  ed25519_hd_key: ^2.3.0
```

### Docker (`docker-compose.yml` additions)

```yaml
  # ─── Polygon RPC (Lightweight) ──────────────────────────────
  # Use Alchemy/Infura in production instead of running a node
  # This is for local development only
  polygon-rpc:
    image: ethereum/client-go:latest
    restart: unless-stopped
    networks:
      - internal
    command: >
      --polygon
      --syncmode light
      --http
      --http.addr 0.0.0.0
      --http.port 8545
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 1G
```

---

## APPENDIX C: KEY DESIGN DECISIONS

| Decision | Chosen | Alternative | Rationale |
|----------|--------|------------|-----------|
| Chain | Polygon PoS | Ethereum L1 | 1000x cheaper gas for frequent miner interactions; sufficient decentralization |
| Voting | Quadratic | Token-weighted | Prevents plutocracy; miners with small holdings still have meaningful voice |
| Token standard | ERC-20 | ERC-721 (NFT) | Governance token needs divisibility; extraction records use NFT separately |
| Oracle model | Multi-submit (3-of-N) | Chainlink DON | Simpler to build; can migrate to Chainlink later; cost-effective |
| Proxy pattern | UUPS | Transparent | Cheaper deployment; same upgrade safety with governance gate |
| Wallet auth | SIWE | Custom JWT+wallet hybrid | Standard (ERC-4361); no custom crypto; compatible with all wallets |
| Data storage | IPFS + on-chain hash | Fully on-chain | Geological data too large for on-chain; hash provides integrity verification |
| Governance timelock | 2-day | 0 (instant) or 7-day | Balance between security and agility for a young DAO |

---

*Report produced by Council 1: DAO Architecture and Blockchain Integration.*
*Analysis based on complete codebase review of mining-super-agent repository.*
*All contract code is illustrative — production contracts require formal verification and professional audit.*
