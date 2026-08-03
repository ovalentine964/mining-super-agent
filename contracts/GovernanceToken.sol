// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title GovernanceToken ($MINE)
 * @notice The governance token for the Sovereign Resource DAO.
 *
 * @dev $MINE is used for:
 *      - Quadratic voting on governance proposals
 *      - Staking for data access tiers
 *      - Royalty claim eligibility (staked tokens receive community wallet share)
 *      - Oracle participation (stake required to run verification nodes)
 *
 *      Distribution:
 *      - 40% Community (miners) — 4yr linear vest, 1yr cliff
 *      - 20% Data Contributors — 3yr linear vest
 *      - 15% Development Team — 4yr linear vest, 2yr cliff
 *      - 15% DAO Treasury — governed by proposals
 *      - 10% Liquidity — no vesting (DEX pool)
 *
 *      Total Supply: 1,000,000,000 $MINE
 */
contract GovernanceToken is ERC20, ERC20Permit, ERC20Votes, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant VESTING_ADMIN = keccak256("VESTING_ADMIN");

    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 1e18; // 1 billion tokens

    // Vesting schedules
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 released;
        uint256 startTime;
        uint256 cliffDuration;  // seconds
        uint256 vestingDuration; // seconds
        bool revocable;
    }

    mapping(address => VestingSchedule) public vestingSchedules;

    // Tracking
    uint256 public totalMinted;
    uint256 public communityAllocated;
    uint256 public contributorAllocated;
    uint256 public teamAllocated;
    uint256 public treasuryAllocated;
    uint256 public liquidityAllocated;

    event TokensVested(
        address indexed beneficiary,
        uint256 amount,
        uint256 cliffEnd,
        uint256 vestingEnd
    );

    event TokensReleased(
        address indexed beneficiary,
        uint256 amount
    );

    constructor()
        ERC20("Sovereign Resource DAO", "MINE")
        ERC20Permit("Sovereign Resource DAO")
    {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(VESTING_ADMIN, msg.sender);
    }

    /// @notice Mint tokens (only by authorized minters)
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(totalMinted + amount <= MAX_SUPPLY, "Exceeds max supply");
        totalMinted += amount;
        _mint(to, amount);
    }

    /// @notice Create a vesting schedule for a beneficiary
    function createVesting(
        address beneficiary,
        uint256 amount,
        uint256 cliffDuration,
        uint256 vestingDuration,
        bool revocable
    ) external onlyRole(VESTING_ADMIN) {
        require(vestingSchedules[beneficiary].totalAmount == 0, "Already vested");
        require(totalMinted + amount <= MAX_SUPPLY, "Exceeds max supply");

        vestingSchedules[beneficiary] = VestingSchedule({
            totalAmount: amount,
            released: 0,
            startTime: block.timestamp,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            revocable: revocable
        });

        totalMinted += amount;
        _mint(address(this), amount); // Hold in contract

        emit TokensVested(
            beneficiary,
            amount,
            block.timestamp + cliffDuration,
            block.timestamp + vestingDuration
        );
    }

    /// @notice Release vested tokens
    function releaseVested() external {
        VestingSchedule storage schedule = vestingSchedules[msg.sender];
        require(schedule.totalAmount > 0, "No vesting schedule");

        uint256 releasable = _calculateReleasable(schedule);
        require(releasable > 0, "Nothing to release");

        schedule.released += releasable;
        _transfer(address(this), msg.sender, releasable);

        emit TokensReleased(msg.sender, releasable);
    }

    function _calculateReleasable(
        VestingSchedule memory schedule
    ) internal view returns (uint256) {
        if (block.timestamp < schedule.startTime + schedule.cliffDuration) {
            return 0; // Still in cliff
        }

        uint256 elapsed = block.timestamp - schedule.startTime;
        if (elapsed >= schedule.vestingDuration) {
            return schedule.totalAmount - schedule.released; // Fully vested
        }

        uint256 vested = (schedule.totalAmount * elapsed) / schedule.vestingDuration;
        return vested - schedule.released;
    }

    // Required overrides for ERC20Votes
    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }

    function _burn(address account, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }
}
