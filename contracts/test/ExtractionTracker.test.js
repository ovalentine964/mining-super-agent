const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ExtractionTracker", function () {
  let tracker;
  let admin, oracle, verifier, community1, community2, other;

  const LOCATION_HASH = ethers.keccak256(
    ethers.toUtf8Bytes("-1.2921,36.8219")
  );
  const LOCATION_HASH_2 = ethers.keccak256(
    ethers.toUtf8Bytes("-1.3000,36.8300")
  );

  beforeEach(async function () {
    [admin, oracle, verifier, community1, community2, other] =
      await ethers.getSigners();

    const ExtractionTracker = await ethers.getContractFactory(
      "ExtractionTracker"
    );
    tracker = await ExtractionTracker.deploy();
    await tracker.waitForDeployment();

    // Grant roles
    const ORACLE_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ORACLE_ROLE"));
    const VERIFIER_ROLE = ethers.keccak256(
      ethers.toUtf8Bytes("VERIFIER_ROLE")
    );

    await tracker.grantRole(ORACLE_ROLE, oracle.address);
    await tracker.grantRole(VERIFIER_ROLE, verifier.address);
  });

  describe("Soulbound NFT Behavior", function () {
    let recordId;

    beforeEach(async function () {
      recordId = await tracker
        .connect(community1)
        .recordExtraction.staticCall(
          LOCATION_HASH,
          "gold",
          500,
          ethers.parseEther("100"),
          8000,
          "ipfs://QmTest123",
          "Rich deposit found near river"
        );

      await tracker
        .connect(community1)
        .recordExtraction(
          LOCATION_HASH,
          "gold",
          500,
          ethers.parseEther("100"),
          8000,
          "ipfs://QmTest123",
          "Rich deposit found near river"
        );
    });

    it("should mint NFT to submitter", async function () {
      expect(await tracker.ownerOf(recordId)).to.equal(community1.address);
      expect(await tracker.balanceOf(community1.address)).to.equal(1);
    });

    it("should prevent transfer (soulbound)", async function () {
      await expect(
        tracker
          .connect(community1)
          .transferFrom(community1.address, community2.address, recordId)
      ).to.be.revertedWith("Soulbound: non-transferable");
    });

    it("should prevent safeTransferFrom", async function () {
      await expect(
        tracker
          .connect(community1)
          ["safeTransferFrom(address,address,uint256)"](
            community1.address,
            community2.address,
            recordId
          )
      ).to.be.revertedWith("Soulbound: non-transferable");
    });

    it("should prevent approve + transferFrom pattern", async function () {
      await expect(
        tracker.connect(community1).approve(community2.address, recordId)
      ).to.be.revertedWith("Soulbound: non-transferable");
    });

    it("should allow minting new records (from address(0))", async function () {
      // Minting is allowed — only transfers are blocked
      await expect(
        tracker.connect(community2).recordExtraction(
          LOCATION_HASH_2,
          "copper",
          300,
          ethers.parseEther("50"),
          7500,
          "ipfs://QmTest456",
          "Copper vein found"
        )
      ).to.not.be.reverted;

      expect(await tracker.ownerOf(1)).to.equal(community2.address);
    });
  });

  describe("Record Extraction", function () {
    it("should create a record with correct data", async function () {
      const tx = await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "ilmenite",
        800,
        ethers.parseEther("500"),
        9000,
        "ipfs://QmIlmenite789",
        "Heavy mineral sands — ilmenite concentration"
      );
      const receipt = await tx.wait();

      const record = await tracker.getRecord(0);
      expect(record.locationHash).to.equal(LOCATION_HASH);
      expect(record.mineralType).to.equal("ilmenite");
      expect(record.estimatedGradeBps).to.equal(800);
      expect(record.estimatedValueKES).to.equal(ethers.parseEther("500"));
      expect(record.confidenceScore).to.equal(9000);
      expect(record.submitter).to.equal(community1.address);
      expect(record.status).to.equal(0); // UNVERIFIED
      expect(record.oracle).to.equal(ethers.ZeroAddress);
      expect(record.ipfsMetadataURI).to.equal("ipfs://QmIlmenite789");
      expect(record.notes).to.equal(
        "Heavy mineral sands — ilmenite concentration"
      );
    });

    it("should emit ExtractionRecorded event", async function () {
      await expect(
        tracker.connect(community1).recordExtraction(
          LOCATION_HASH,
          "gold",
          500,
          ethers.parseEther("100"),
          8000,
          "ipfs://QmTest",
          "notes"
        )
      )
        .to.emit(tracker, "ExtractionRecorded")
        .withArgs(
          0,
          community1.address,
          LOCATION_HASH,
          "gold",
          0 // UNVERIFIED
        );
    });

    it("should increment record IDs sequentially", async function () {
      await tracker
        .connect(community1)
        .recordExtraction(
          LOCATION_HASH,
          "gold",
          100,
          1000,
          5000,
          "ipfs://1",
          ""
        );

      await tracker
        .connect(community2)
        .recordExtraction(
          LOCATION_HASH_2,
          "copper",
          200,
          2000,
          6000,
          "ipfs://2",
          ""
        );

      const record0 = await tracker.getRecord(0);
      const record1 = await tracker.getRecord(1);

      expect(record0.submitter).to.equal(community1.address);
      expect(record1.submitter).to.equal(community2.address);
    });

    it("should index records by location", async function () {
      await tracker
        .connect(community1)
        .recordExtraction(
          LOCATION_HASH,
          "gold",
          100,
          1000,
          5000,
          "ipfs://1",
          ""
        );
      await tracker
        .connect(community2)
        .recordExtraction(
          LOCATION_HASH,
          "gold",
          200,
          2000,
          6000,
          "ipfs://2",
          ""
        );
      await tracker
        .connect(community1)
        .recordExtraction(
          LOCATION_HASH_2,
          "copper",
          300,
          3000,
          7000,
          "ipfs://3",
          ""
        );

      const loc1Records = await tracker.getLocationRecords(LOCATION_HASH);
      const loc2Records = await tracker.getLocationRecords(LOCATION_HASH_2);

      expect(loc1Records.length).to.equal(2);
      expect(loc1Records[0]).to.equal(0);
      expect(loc1Records[1]).to.equal(1);
      expect(loc2Records.length).to.equal(1);
      expect(loc2Records[0]).to.equal(2);
    });

    it("should increment totalRecords", async function () {
      expect(await tracker.totalRecords()).to.equal(0);

      await tracker
        .connect(community1)
        .recordExtraction(
          LOCATION_HASH,
          "gold",
          100,
          1000,
          5000,
          "ipfs://1",
          ""
        );
      expect(await tracker.totalRecords()).to.equal(1);

      await tracker
        .connect(community2)
        .recordExtraction(
          LOCATION_HASH_2,
          "copper",
          200,
          2000,
          6000,
          "ipfs://2",
          ""
        );
      expect(await tracker.totalRecords()).to.equal(2);
    });
  });

  describe("Oracle Verification", function () {
    let recordId;

    beforeEach(async function () {
      await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "gold",
        500,
        ethers.parseEther("100"),
        8000,
        "ipfs://QmTest",
        "notes"
      );
      recordId = 0;
    });

    it("should allow oracle to verify valid extraction", async function () {
      await expect(
        tracker.connect(oracle).verifyExtraction(recordId, true, 9500)
      )
        .to.emit(tracker, "ExtractionVerified")
        .withArgs(recordId, oracle.address, 1, 9500); // ORACLE_VERIFIED = 1

      const record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(1); // ORACLE_VERIFIED
      expect(record.confidenceScore).to.equal(9500);
      expect(record.oracle).to.equal(oracle.address);
      expect(record.oracleTimestamp).to.be.gt(0);
    });

    it("should mark invalid extraction as disputed", async function () {
      await tracker.connect(oracle).verifyExtraction(recordId, false, 0);

      const record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(3); // DISPUTED
      expect(record.oracle).to.equal(oracle.address);
    });

    it("should increment verifiedRecords on valid verification", async function () {
      expect(await tracker.verifiedRecords()).to.equal(0);
      await tracker.connect(oracle).verifyExtraction(recordId, true, 9000);
      expect(await tracker.verifiedRecords()).to.equal(1);
    });

    it("should increment disputedRecords on invalid verification", async function () {
      expect(await tracker.disputedRecords()).to.equal(0);
      await tracker.connect(oracle).verifyExtraction(recordId, false, 0);
      expect(await tracker.disputedRecords()).to.equal(1);
    });

    it("should reject non-oracle callers", async function () {
      await expect(
        tracker.connect(community1).verifyExtraction(recordId, true, 9000)
      ).to.be.reverted;
    });

    it("should reject verification of non-existent record", async function () {
      await expect(
        tracker.connect(oracle).verifyExtraction(999, true, 9000)
      ).to.be.revertedWith("Record does not exist");
    });
  });

  describe("Community Confirmation", function () {
    let recordId;

    beforeEach(async function () {
      await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "gold",
        500,
        ethers.parseEther("100"),
        8000,
        "ipfs://QmTest",
        "notes"
      );
      recordId = 0;

      // Oracle verifies first
      await tracker.connect(oracle).verifyExtraction(recordId, true, 9000);
    });

    it("should allow verifier to confirm oracle-verified record", async function () {
      await tracker.connect(verifier).communityConfirm(recordId);

      const record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(2); // COMMUNITY_CONFIRMED
    });

    it("should reject confirmation of unverified record", async function () {
      // Create a new unverified record
      await tracker.connect(community2).recordExtraction(
        LOCATION_HASH_2,
        "copper",
        300,
        3000,
        7000,
        "ipfs://QmTest2",
        "notes"
      );

      await expect(
        tracker.connect(verifier).communityConfirm(1)
      ).to.be.revertedWith("Must be oracle-verified first");
    });

    it("should reject non-verifier callers", async function () {
      await expect(
        tracker.connect(community1).communityConfirm(recordId)
      ).to.be.reverted;
    });
  });

  describe("Dispute Extraction", function () {
    let recordId;

    beforeEach(async function () {
      await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "gold",
        500,
        ethers.parseEther("100"),
        8000,
        "ipfs://QmTest",
        "notes"
      );
      recordId = 0;
    });

    it("should allow anyone to dispute a record", async function () {
      await expect(
        tracker
          .connect(other)
          .disputeExtraction(recordId, "Coordinates don't match satellite data")
      )
        .to.emit(tracker, "ExtractionDisputed")
        .withArgs(
          recordId,
          other.address,
          "Coordinates don't match satellite data"
        );

      const record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(3); // DISPUTED
    });

    it("should increment disputedRecords", async function () {
      expect(await tracker.disputedRecords()).to.equal(0);
      await tracker
        .connect(other)
        .disputeExtraction(recordId, "Fake data");
      expect(await tracker.disputedRecords()).to.equal(1);
    });

    it("should reject dispute of non-existent record", async function () {
      await expect(
        tracker.connect(other).disputeExtraction(999, "reason")
      ).to.be.revertedWith("Record does not exist");
    });
  });

  describe("Verification Flow End-to-End", function () {
    it("should follow full flow: submit → verify → confirm", async function () {
      // 1. Community member submits
      const tx = await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "ilmenite",
        800,
        ethers.parseEther("500"),
        7000,
        "ipfs://QmFullFlow",
        "Heavy mineral sands"
      );
      await tx.wait();

      const recordId = 0;

      // Check initial state
      let record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(0); // UNVERIFIED

      // 2. Oracle verifies
      await tracker.connect(oracle).verifyExtraction(recordId, true, 8500);
      record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(1); // ORACLE_VERIFIED
      expect(record.confidenceScore).to.equal(8500);

      // 3. Community confirms
      await tracker.connect(verifier).communityConfirm(recordId);
      record = await tracker.getRecord(recordId);
      expect(record.status).to.equal(2); // COMMUNITY_CONFIRMED

      // Stats
      const [total, verified, disputed] = await tracker.getStats();
      expect(total).to.equal(1);
      expect(verified).to.equal(1);
      expect(disputed).to.equal(0);
    });

    it("should follow dispute flow: submit → dispute", async function () {
      await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "gold",
        100,
        1000,
        2000,
        "ipfs://QmDispute",
        "Suspicious claim"
      );

      await tracker
        .connect(other)
        .disputeExtraction(0, "Location is in a national park");

      const record = await tracker.getRecord(0);
      expect(record.status).to.equal(3); // DISPUTED
    });
  });

  describe("View Functions", function () {
    it("getLocationRecords returns empty array for unknown location", async function () {
      const unknown = ethers.keccak256(ethers.toUtf8Bytes("nowhere"));
      const records = await tracker.getLocationRecords(unknown);
      expect(records.length).to.equal(0);
    });

    it("getStats returns correct aggregate stats", async function () {
      // Submit 3 records
      for (let i = 0; i < 3; i++) {
        await tracker.connect(community1).recordExtraction(
          LOCATION_HASH,
          "gold",
          100,
          1000,
          5000,
          `ipfs://Qm${i}`,
          ""
        );
      }

      // Verify 2, dispute 1
      await tracker.connect(oracle).verifyExtraction(0, true, 8000);
      await tracker.connect(oracle).verifyExtraction(1, true, 9000);
      await tracker.connect(oracle).verifyExtraction(2, false, 1000);

      const [total, verified, disputed] = await tracker.getStats();
      expect(total).to.equal(3);
      expect(verified).to.equal(2);
      expect(disputed).to.equal(1);
    });
  });

  describe("NFT Metadata", function () {
    it("should set token URI from IPFS metadata", async function () {
      await tracker.connect(community1).recordExtraction(
        LOCATION_HASH,
        "gold",
        500,
        ethers.parseEther("100"),
        8000,
        "ipfs://QmMetadata123",
        "notes"
      );

      expect(await tracker.tokenURI(0)).to.equal("ipfs://QmMetadata123");
    });

    it("should support ERC721 interface", async function () {
      // ERC721 interface ID: 0x80ac58cd
      expect(await tracker.supportsInterface("0x80ac58cd")).to.be.true;
    });
  });
});
