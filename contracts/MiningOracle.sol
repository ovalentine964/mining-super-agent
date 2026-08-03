// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title MiningOracle
 * @notice On-chain oracle for mineral data verification.
 *
 * @dev The oracle bridge (Python → Polygon) submits data from the AI super-agent.
 *      Multiple oracles can submit for the same location, and consensus is required.
 *      This prevents a single compromised oracle from corrupting the data.
 *
 *      Data flow:
 *      Community member submits photo/GPS → AI agent analyzes →
 *      Oracle bridge submits to chain → Multiple oracles verify →
 *      ExtractionTracker records verified data
 */
contract MiningOracle is AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant ORACLE_ADMIN = keccak256("ORACLE_ADMIN");

    struct OracleSubmission {
        bytes32 locationHash;
        string mineralType;
        uint256 estimatedValueKES;
        uint256 confidenceBps;       // 0-10000 basis points
        bytes32 dataHash;            // Hash of full data (for integrity)
        address oracle;
        uint256 timestamp;
        bool verified;
    }

    // Multiple oracles can submit for the same location
    mapping(bytes32 => OracleSubmission[]) public submissions;
    mapping(bytes32 => bool) public locationVerified;
    mapping(bytes32 => uint256) public submissionCount;
    mapping(address => bool) public activeOracles;
    mapping(bytes32 => mapping(address => bool)) public hasSubmitted; // C-2 fix: per-oracle-per-location duplicate prevention

    // Consensus threshold
    uint256 public requiredConfirmations = 2;

    event OracleSubmitted(
        bytes32 indexed locationHash,
        address indexed oracle,
        string mineralType,
        uint256 confidenceBps
    );

    event LocationVerified(
        bytes32 indexed locationHash,
        uint256 confirmationCount,
        uint256 averageConfidence
    );

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ORACLE_ADMIN, msg.sender);
    }

    /// @notice Submit oracle data for a location
    function submitData(
        bytes32 locationHash,
        string calldata mineralType,
        uint256 estimatedValueKES,
        uint256 confidenceBps,
        bytes32 dataHash
    ) external onlyRole(ORACLE_ROLE) {
        require(confidenceBps <= 10000, "Confidence exceeds 100%");
        require(!locationVerified[locationHash], "Already verified");
        require(!hasSubmitted[locationHash][msg.sender], "Already submitted"); // C-2 fix
        hasSubmitted[locationHash][msg.sender] = true; // C-2 fix

        submissions[locationHash].push(OracleSubmission({
            locationHash: locationHash,
            mineralType: mineralType,
            estimatedValueKES: estimatedValueKES,
            confidenceBps: confidenceBps,
            dataHash: dataHash,
            oracle: msg.sender,
            timestamp: block.timestamp,
            verified: false
        }));

        submissionCount[locationHash]++;
        activeOracles[msg.sender] = true;

        emit OracleSubmitted(
            locationHash, msg.sender, mineralType, confidenceBps
        );

        // Check if we have enough confirmations
        if (submissionCount[locationHash] >= requiredConfirmations) {
            _verifyLocation(locationHash);
        }
    }

    /// @notice Verify a location once enough oracle submissions exist
    function _verifyLocation(bytes32 locationHash) internal {
        OracleSubmission[] storage subs = submissions[locationHash];
        uint256 totalConfidence = 0;
        uint256 verifiedCount = 0;

        for (uint i = 0; i < subs.length; i++) {
            if (subs[i].oracle != address(0)) {
                subs[i].verified = true;
                totalConfidence += subs[i].confidenceBps;
                verifiedCount++;
            }
        }

        uint256 avgConfidence = verifiedCount > 0
            ? totalConfidence / verifiedCount
            : 0;

        locationVerified[locationHash] = true;

        emit LocationVerified(
            locationHash, verifiedCount, avgConfidence
        );
    }

    /// @notice Get all submissions for a location
    function getSubmissions(
        bytes32 locationHash
    ) external view returns (OracleSubmission[] memory) {
        return submissions[locationHash];
    }

    /// @notice Check if a location is verified
    function isVerified(bytes32 locationHash) external view returns (bool) {
        return locationVerified[locationHash];
    }

    /// @notice Get submission count for a location
    function getSubmissionCount(bytes32 locationHash) external view returns (uint256) {
        return submissionCount[locationHash];
    }

    /// @notice Update required confirmations (admin only)
    function setRequiredConfirmations(uint256 _required) external onlyRole(ORACLE_ADMIN) {
        require(_required >= 2, "Minimum 2 confirmations required"); // M-2 fix
        requiredConfirmations = _required;
    }
}
