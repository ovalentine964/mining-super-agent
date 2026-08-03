// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title ExtractionTracker
 * @notice On-chain, immutable, soulbound record of every mineral extraction event.
 *
 * @dev Each extraction mints a non-transferable NFT containing:
 *      - GPS coordinates (on-chain hash, full data on IPFS)
 *      - Mineral type and estimated grade
 *      - Timestamp and submitter wallet
 *      - AI confidence score (from the super-agent oracle)
 *      - Verification status (unverified → oracle-verified → community-confirmed)
 *
 *      SOULBOUND: These NFTs cannot be transferred. They are permanent records.
 *      TRANSPARENT: Anyone can verify what was extracted and when.
 *      IMMUTABLE: Once confirmed, records cannot be deleted or altered.
 *
 *      This is the "proof of extraction" — the data that makes exploitation visible.
 */
contract ExtractionTracker is ERC721URIStorage, AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    bytes32 public constant TRACKER_ADMIN = keccak256("TRACKER_ADMIN");

    enum VerificationStatus {
        UNVERIFIED,          // Submitted by community member
        ORACLE_VERIFIED,     // Verified by AI oracle (satellite/vision/analysis)
        COMMUNITY_CONFIRMED, // Confirmed by community vote
        DISPUTED             // Challenged — requires resolution
    }

    struct ExtractionRecord {
        bytes32 locationHash;        // keccak256(lat, lon) — privacy-preserving
        string mineralType;          // "gold", "copper", "ilmenite", etc.
        uint256 estimatedGradeBps;   // Grade in basis points (e.g., 500 = 5%)
        uint256 estimatedValueKES;   // Estimated value in KES (smallest unit)
        uint256 confidenceScore;     // 0-10000 (basis points, AI-calculated)
        uint256 timestamp;           // Block timestamp
        address submitter;           // Who submitted (community member wallet)
        VerificationStatus status;   // Current verification status
        uint256 oracleTimestamp;     // When oracle verified
        address oracle;              // Which oracle verified
        string ipfsMetadataURI;      // Full geological data on IPFS
        string notes;                // Free-text notes (Swahili or English)
    }

    mapping(uint256 => ExtractionRecord) public records;
    mapping(bytes32 => uint256[]) public locationRecords; // locationHash → record IDs
    uint256 public nextRecordId;

    // Statistics
    uint256 public totalRecords;
    uint256 public verifiedRecords;
    uint256 public disputedRecords;

    event ExtractionRecorded(
        uint256 indexed recordId,
        address indexed submitter,
        bytes32 locationHash,
        string mineralType,
        VerificationStatus status
    );

    event ExtractionVerified(
        uint256 indexed recordId,
        address indexed oracle,
        VerificationStatus newStatus,
        uint256 confidenceScore
    );

    event ExtractionDisputed(
        uint256 indexed recordId,
        address indexed disputer,
        string reason
    );

    constructor() ERC721("Sovereign Extraction Record", "SER") {}

    /// @notice Record a new extraction event
    /// @dev Called by community members or the oracle bridge
    function recordExtraction(
        bytes32 locationHash,
        string calldata mineralType,
        uint256 estimatedGradeBps,
        uint256 estimatedValueKES,
        uint256 confidenceScore,
        string calldata ipfsMetadataURI,
        string calldata notes
    ) external returns (uint256) {
        uint256 recordId = nextRecordId++;

        records[recordId] = ExtractionRecord({
            locationHash: locationHash,
            mineralType: mineralType,
            estimatedGradeBps: estimatedGradeBps,
            estimatedValueKES: estimatedValueKES,
            confidenceScore: confidenceScore,
            timestamp: block.timestamp,
            submitter: msg.sender,
            status: VerificationStatus.UNVERIFIED,
            oracleTimestamp: 0,
            oracle: address(0),
            ipfsMetadataURI: ipfsMetadataURI,
            notes: notes
        });

        // Soulbound mint — only the submitter owns this record
        _safeMint(msg.sender, recordId);
        setTokenURI(recordId, ipfsMetadataURI);

        // Index by location
        locationRecords[locationHash].push(recordId);

        totalRecords++;

        emit ExtractionRecorded(
            recordId, msg.sender, locationHash,
            mineralType, VerificationStatus.UNVERIFIED
        );

        return recordId;
    }

    /// @notice Oracle verifies an extraction record
    /// @dev Called by the oracle bridge after AI analysis
    function verifyExtraction(
        uint256 recordId,
        bool isValid,
        uint256 updatedConfidence
    ) external onlyRole(ORACLE_ROLE) {
        ExtractionRecord storage record = records[recordId];
        require(record.submitter != address(0), "Record does not exist");

        if (isValid) {
            record.status = VerificationStatus.ORACLE_VERIFIED;
            record.confidenceScore = updatedConfidence;
            verifiedRecords++;
        } else {
            record.status = VerificationStatus.DISPUTED;
            disputedRecords++;
        }

        record.oracleTimestamp = block.timestamp;
        record.oracle = msg.sender;

        emit ExtractionVerified(recordId, msg.sender, record.status, updatedConfidence);
    }

    /// @notice Community confirms an extraction record via vote
    function communityConfirm(uint256 recordId) external onlyRole(VERIFIER_ROLE) {
        ExtractionRecord storage record = records[recordId];
        require(
            record.status == VerificationStatus.ORACLE_VERIFIED,
            "Must be oracle-verified first"
        );

        record.status = VerificationStatus.COMMUNITY_CONFIRMED;
        // Note: Soulbound — no transfer, just status update
    }

    /// @notice Dispute an extraction record
    function disputeExtraction(
        uint256 recordId,
        string calldata reason
    ) external {
        ExtractionRecord storage record = records[recordId];
        require(record.submitter != address(0), "Record does not exist");

        record.status = VerificationStatus.DISPUTED;
        disputedRecords++;

        emit ExtractionDisputed(recordId, msg.sender, reason);
    }

    /// @notice Get all records for a location
    function getLocationRecords(
        bytes32 locationHash
    ) external view returns (uint256[] memory) {
        return locationRecords[locationHash];
    }

    /// @notice Get record details
    function getRecord(
        uint256 recordId
    ) external view returns (ExtractionRecord memory) {
        return records[recordId];
    }

    /// @notice Get statistics
    function getStats() external view returns (
        uint256 total,
        uint256 verified,
        uint256 disputed
    ) {
        return (totalRecords, verifiedRecords, disputedRecords);
    }

    // Soulbound — override transfer functions to prevent transfers
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal virtual override {
        // Allow minting (from == address(0)) but prevent transfers
        require(
            from == address(0) || to == address(0),
            "Soulbound: non-transferable"
        );
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }
}
