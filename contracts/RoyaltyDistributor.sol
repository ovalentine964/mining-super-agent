// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title RoyaltyDistributor
 * @notice Automatically splits all incoming revenue:
 *         70% → Community Development Fund (schools, healthcare, infrastructure)
 *         20% → Community Wallet (direct payments to verified miners/data contributors)
 *         10% → Protocol Reserve (insurance, emergencies, audits, legal defense)
 *
 * @dev Based on Council 1 DAO Architecture design.
 *      UUPS proxy pattern for upgradability (governance-gated).
 *      All splits are immutable in logic but percentages are
 *      adjustable via DAO vote (within bounds).
 *
 *      THE CORE PRINCIPLE: No human touches the money.
 *      Revenue flows in → Smart contract splits → Wallets receive.
 *      No politician can steal what they can't access.
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

    // Boundaries (cannot be changed even by DAO — protects community)
    uint256 public constant MIN_COMMUNITY_SHARE = 5000; // Min 50% to community
    uint256 public constant MAX_RESERVE_SHARE = 2000;   // Max 20% to reserve

    // Destination wallets
    address public communityDevelopmentFund;
    address public communityWallet;
    address public protocolReserve;

    // Royalty sources — where the money comes from
    enum RoyaltySource {
        DATA_LICENSING,     // Institutions paying for aggregated mineral intelligence
        EXTRACTION,         // Mining operations paying community royalties
        PLATFORM_FEE,       // Transaction fees on DAO marketplace
        DONATION,           // Direct donations
        RECOVERY            // Recovered unpaid royalties (from legal action)
    }

    // M-5 fix: pending withdrawals fallback for failed transfers
    mapping(address => uint256) public pendingWithdrawals;

    // Tracking
    uint256 public totalDistributed;
    uint256 public lastDistributionTimestamp;
    uint256 public distributionCount;

    // Events for off-chain indexing
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

    event DestinationUpdated(
        address indexed fund,
        string fundType,
        uint256 timestamp
    );

    /// @notice Initialize the contract (called once via proxy)
    function initialize(
        address _communityDevelopmentFund,
        address _communityWallet,
        address _protocolReserve,
        address _admin
    ) public initializer {
        __UUPSUpgradeable_init();
        __AccessControl_init();
        __ReentrancyGuard_init();

        require(_communityDevelopmentFund != address(0), "Zero address: dev fund"); // H-3 fix
        require(_communityWallet != address(0), "Zero address: community wallet"); // H-3 fix
        require(_protocolReserve != address(0), "Zero address: reserve"); // H-3 fix

        communityDevelopmentFund = _communityDevelopmentFund;
        communityWallet = _communityWallet;
        protocolReserve = _protocolReserve;

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(DAO_ROLE, _admin);
        _grantRole(DISTRIBUTOR_ADMIN, _admin);
    }

    /// @notice Receive and distribute revenue automatically
    /// @dev Anyone can send revenue. The contract splits it instantly.
    ///      No human decision. No politician approval. Math is the law.
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
        distributionCount++;
        lastDistributionTimestamp = block.timestamp;

        // M-5 fix: try/catch pattern with pendingWithdrawals fallback
        // Transfer shares — non-blocking, bad destination doesn't block others
        (bool devOk, ) = communityDevelopmentFund.call{value: devShare}("");
        if (!devOk) {
            pendingWithdrawals[communityDevelopmentFund] += devShare;
        }

        (bool walletOk, ) = communityWallet.call{value: walletShare}("");
        if (!walletOk) {
            pendingWithdrawals[communityWallet] += walletShare;
        }

        (bool reserveOk, ) = protocolReserve.call{value: reserveShare}("");
        if (!reserveOk) {
            pendingWithdrawals[protocolReserve] += reserveShare;
        }

        emit RevenueDistributed(
            msg.sender, source, msg.value,
            devShare, walletShare, reserveShare, block.timestamp
        );
    }

    /// @notice Update split percentages (DAO-only, within bounds)
    /// @dev Can only be called by DAO governance vote
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

    /// @notice Update destination wallets (DAO-only) (H-3 fix: zero address validation)
    function updateDestinations(
        address _devFund,
        address _communityWallet,
        address _reserve
    ) external onlyRole(DAO_ROLE) {
        if (_devFund != address(0)) {
            require(_devFund != address(0), "Zero address: dev fund");
            communityDevelopmentFund = _devFund;
            emit DestinationUpdated(_devFund, "development", block.timestamp);
        }
        if (_communityWallet != address(0)) {
            require(_communityWallet != address(0), "Zero address: community wallet");
            communityWallet = _communityWallet;
            emit DestinationUpdated(_communityWallet, "community", block.timestamp);
        }
        if (_reserve != address(0)) {
            require(_reserve != address(0), "Zero address: reserve");
            protocolReserve = _reserve;
            emit DestinationUpdated(_reserve, "reserve", block.timestamp);
        }
    }

    /// @notice Get current split configuration
    function getSplits() external view returns (
        uint256 devBps,
        uint256 walletBps,
        uint256 reserveBps
    ) {
        return (communityDevelopmentBps, communityWalletBps, reserveBps);
    }

    /// @notice Get distribution statistics
    function getStats() external view returns (
        uint256 total,
        uint256 count,
        uint256 lastTimestamp
    ) {
        return (totalDistributed, distributionCount, lastDistributionTimestamp);
    }

    /// @notice Withdraw pending funds after a failed distribution (M-5 fix)
    function withdrawPending() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "No pending withdrawal");
        pendingWithdrawals[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
    }

    // UUPS authorization — only DAO can upgrade
    function _authorizeUpgrade(address newImplementation)
        internal override onlyRole(DAO_ROLE) {}
}
