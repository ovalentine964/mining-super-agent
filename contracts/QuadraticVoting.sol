// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title QuadraticVoting
 * @notice Quadratic voting mechanism for the Sovereign Resource DAO.
 *
 * @dev Voting power = sqrt(tokens committed). This prevents plutocratic control
 *      while still giving larger stakeholders more influence.
 *
 *      1 token  = 1 vote
 *      4 tokens = 2 votes
 *      9 tokens = 3 votes
 *      100 tokens = 10 votes
 *      10000 tokens = 100 votes
 *
 *      This means a whale with 10000x more tokens only has 100x more voting power.
 *      The community's voice is amplified. Wealth cannot buy decisions.
 */
contract QuadraticVoting is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant VOTING_ADMIN = keccak256("VOTING_ADMIN");

    struct Vote {
        uint256 proposalId;
        address voter;
        uint256 tokensCommitted;     // Actual tokens locked
        uint256 quadraticPower;      // sqrt(tokensCommitted) * 1e18
        bool support;                // true = for, false = against
        uint256 timestamp;
    }

    IERC20 public immutable governanceToken;

    uint256 public constant PRECISION = 1e18;
    uint256 public constant VOTE_LOCK_DURATION = 7 days;
    uint256 public constant MINIMUM_TOKENS = 1e18; // Minimum 1 token to vote

    // Proposal vote tracking
    mapping(uint256 => mapping(address => Vote)) public votes;
    mapping(uint256 => uint256) public totalForPower;
    mapping(uint256 => uint256) public totalAgainstPower;
    mapping(uint256 => uint256) public totalTokensLocked;
    mapping(uint256 => uint256) public voterCount;

    // Token unlock tracking
    mapping(uint256 => mapping(address => uint256)) public unlockTime;

    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        uint256 tokensCommitted,
        uint256 quadraticPower,
        bool support
    );

    event VoteWithdrawn(
        uint256 indexed proposalId,
        address indexed voter,
        uint256 tokensReturned
    );

    constructor(address _governanceToken) {
        governanceToken = IERC20(_governanceToken);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(VOTING_ADMIN, msg.sender);
    }

    /// @notice Cast a quadratic vote on a proposal
    /// @param proposalId The proposal to vote on
    /// @param tokens Amount of $MINE tokens to commit (locked for VOTE_LOCK_DURATION)
    /// @param support true = for, false = against
    function castVote(
        uint256 proposalId,
        uint256 tokens,
        bool support
    ) external nonReentrant {
        require(tokens >= MINIMUM_TOKENS, "Below minimum tokens");
        require(
            votes[proposalId][msg.sender].tokensCommitted == 0,
            "Already voted on this proposal"
        );

        // Calculate quadratic power: sqrt(tokens) * PRECISION
        uint256 quadraticPower = _sqrt(tokens * PRECISION);

        // Transfer tokens to contract (locked)
        governanceToken.safeTransferFrom(msg.sender, address(this), tokens);

        // Record vote
        votes[proposalId][msg.sender] = Vote({
            proposalId: proposalId,
            voter: msg.sender,
            tokensCommitted: tokens,
            quadraticPower: quadraticPower,
            support: support,
            timestamp: block.timestamp
        });

        // Update totals
        if (support) {
            totalForPower[proposalId] += quadraticPower;
        } else {
            totalAgainstPower[proposalId] += quadraticPower;
        }
        totalTokensLocked[proposalId] += tokens;
        voterCount[proposalId]++;

        // Set unlock time
        unlockTime[proposalId][msg.sender] = block.timestamp + VOTE_LOCK_DURATION;

        emit VoteCast(proposalId, msg.sender, tokens, quadraticPower, support);
    }

    /// @withdraw Withdraw tokens after lock period
    function withdrawVote(uint256 proposalId) external nonReentrant {
        Vote storage vote = votes[proposalId][msg.sender];
        require(vote.tokensCommitted > 0, "No vote to withdraw");
        require(
            block.timestamp >= unlockTime[proposalId][msg.sender],
            "Tokens still locked"
        );

        uint256 tokens = vote.tokensCommitted;

        // Clear vote
        delete votes[proposalId][msg.sender];
        totalTokensLocked[proposalId] -= tokens;

        // Return tokens
        governanceToken.safeTransfer(msg.sender, tokens);

        emit VoteWithdrawn(proposalId, msg.sender, tokens);
    }

    /// @notice Get vote results for a proposal
    function getVoteResults(uint256 proposalId) external view returns (
        uint256 forPower,
        uint256 againstPower,
        uint256 totalVoters,
        uint256 totalLocked
    ) {
        return (
            totalForPower[proposalId],
            totalAgainstPower[proposalId],
            voterCount[proposalId],
            totalTokensLocked[proposalId]
        );
    }

    /// @notice Check if a proposal has passed (simple majority of quadratic power)
    function hasProposalPassed(uint256 proposalId) external view returns (bool) {
        uint256 forPower = totalForPower[proposalId];
        uint256 againstPower = totalAgainstPower[proposalId];
        uint256 total = forPower + againstPower;

        if (total == 0) return false;

        // Requires >50% of quadratic power AND minimum participation
        return forPower > againstPower && total >= 100 * PRECISION;
    }

    /// @notice Get a voter's details for a proposal
    function getVote(
        uint256 proposalId,
        address voter
    ) external view returns (Vote memory) {
        return votes[proposalId][voter];
    }

    /// @notice Integer square root (Babylonian method)
    function _sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }
}
