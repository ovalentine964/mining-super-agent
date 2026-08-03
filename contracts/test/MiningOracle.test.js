const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MiningOracle", function () {
  let oracle;
  let admin, oracle1, oracle2, oracle3, nonOracle;

  const LOCATION_HASH = ethers.keccak256(
    ethers.toUtf8Bytes("-1.2921,36.8219")
  );
  const LOCATION_HASH_2 = ethers.keccak256(
    ethers.toUtf8Bytes("-1.3000,36.8300")
  );
  const DATA_HASH = ethers.keccak256(ethers.toUtf8Bytes("full-geological-data"));

  beforeEach(async function () {
    [admin, oracle1, oracle2, oracle3, nonOracle] = await ethers.getSigners();

    const MiningOracle = await ethers.getContractFactory("MiningOracle");
    oracle = await MiningOracle.deploy();
    await oracle.waitForDeployment();

    // Grant ORACLE_ROLE to oracle accounts
    const ORACLE_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ORACLE_ROLE"));
    await oracle.grantRole(ORACLE_ROLE, oracle1.address);
    await oracle.grantRole(ORACLE_ROLE, oracle2.address);
    await oracle.grantRole(ORACLE_ROLE, oracle3.address);
  });

  describe("Initialization", function () {
    it("should set correct default required confirmations", async function () {
      expect(await oracle.requiredConfirmations()).to.equal(2);
    });

    it("should grant admin roles to deployer", async function () {
      const DEFAULT_ADMIN_ROLE =
        "0x0000000000000000000000000000000000000000000000000000000000000000";
      const ORACLE_ADMIN = ethers.keccak256(
        ethers.toUtf8Bytes("ORACLE_ADMIN")
      );

      expect(await oracle.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be
        .true;
      expect(await oracle.hasRole(ORACLE_ADMIN, admin.address)).to.be.true;
    });

    it("should start with no verified locations", async function () {
      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;
    });

    it("should start with zero submission count", async function () {
      expect(await oracle.getSubmissionCount(LOCATION_HASH)).to.equal(0);
    });
  });

  describe("Submit Data", function () {
    it("should allow oracle to submit data", async function () {
      await expect(
        oracle.connect(oracle1).submitData(
          LOCATION_HASH,
          "gold",
          ethers.parseEther("100"),
          8500,
          DATA_HASH
        )
      )
        .to.emit(oracle, "OracleSubmitted")
        .withArgs(LOCATION_HASH, oracle1.address, "gold", 8500);
    });

    it("should store submission correctly", async function () {
      await oracle
        .connect(oracle1)
        .submitData(
          LOCATION_HASH,
          "ilmenite",
          ethers.parseEther("500"),
          9000,
          DATA_HASH
        );

      const submissions = await oracle.getSubmissions(LOCATION_HASH);
      expect(submissions.length).to.equal(1);

      const sub = submissions[0];
      expect(sub.locationHash).to.equal(LOCATION_HASH);
      expect(sub.mineralType).to.equal("ilmenite");
      expect(sub.estimatedValueKES).to.equal(ethers.parseEther("500"));
      expect(sub.confidenceBps).to.equal(9000);
      expect(sub.dataHash).to.equal(DATA_HASH);
      expect(sub.oracle).to.equal(oracle1.address);
      expect(sub.timestamp).to.be.gt(0);
      expect(sub.verified).to.be.false;
    });

    it("should increment submission count", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);

      expect(await oracle.getSubmissionCount(LOCATION_HASH)).to.equal(1);
    });

    it("should track active oracles", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);

      expect(await oracle.activeOracles(oracle1.address)).to.be.true;
      expect(await oracle.activeOracles(oracle2.address)).to.be.false;
    });

    it("should reject non-oracle callers", async function () {
      await expect(
        oracle
          .connect(nonOracle)
          .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH)
      ).to.be.reverted;
    });

    it("should reject confidence > 10000", async function () {
      await expect(
        oracle
          .connect(oracle1)
          .submitData(LOCATION_HASH, "gold", 1000, 10001, DATA_HASH)
      ).to.be.revertedWith("Confidence exceeds 100%");
    });

    it("should allow confidence = 10000 (exactly 100%)", async function () {
      await expect(
        oracle
          .connect(oracle1)
          .submitData(LOCATION_HASH, "gold", 1000, 10000, DATA_HASH)
      ).to.not.be.reverted;
    });

    it("should reject submission to already-verified location", async function () {
      // Submit 2 to verify
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH);

      // Location is now verified
      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;

      // Third submission should fail
      await expect(
        oracle
          .connect(oracle3)
          .submitData(LOCATION_HASH, "gold", 1000, 8500, DATA_HASH)
      ).to.be.revertedWith("Already verified");
    });
  });

  describe("Consensus Mechanism", function () {
    it("should NOT verify with only 1 submission (requires 2)", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;
    });

    it("should verify with 2 submissions (default threshold)", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);

      await expect(
        oracle
          .connect(oracle2)
          .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH)
      )
        .to.emit(oracle, "LocationVerified")
        .withArgs(
          LOCATION_HASH,
          2, // confirmation count
          8500 // average confidence (8000 + 9000) / 2
        );

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;
    });

    it("should mark all submissions as verified after consensus", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH);

      const submissions = await oracle.getSubmissions(LOCATION_HASH);
      expect(submissions[0].verified).to.be.true;
      expect(submissions[1].verified).to.be.true;
    });

    it("should compute average confidence correctly", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 7000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH);
      await oracle
        .connect(oracle3)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);

      // All 3 submissions should be verified (2 triggered it, 3rd adds to it)
      const submissions = await oracle.getSubmissions(LOCATION_HASH);
      for (const sub of submissions) {
        expect(sub.verified).to.be.true;
      }
    });

    it("should handle 3-oracle consensus", async function () {
      // Set required confirmations to 3
      await oracle.connect(admin).setRequiredConfirmations(3);

      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "copper", 2000, 7500, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "copper", 2000, 8500, DATA_HASH);

      // Not yet verified with only 2
      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;

      // Third submission triggers verification
      await expect(
        oracle
          .connect(oracle3)
          .submitData(LOCATION_HASH, "copper", 2000, 9000, DATA_HASH)
      )
        .to.emit(oracle, "LocationVerified")
        .withArgs(LOCATION_HASH, 3, 8333); // (7500 + 8500 + 9000) / 3 = 8333

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;
    });
  });

  describe("Multiple Locations", function () {
    it("should track submissions independently per location", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH_2, "copper", 2000, 7000, DATA_HASH);

      expect(await oracle.getSubmissionCount(LOCATION_HASH)).to.equal(1);
      expect(await oracle.getSubmissionCount(LOCATION_HASH_2)).to.equal(1);

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;
      expect(await oracle.isVerified(LOCATION_HASH_2)).to.be.false;
    });

    it("should verify locations independently", async function () {
      // Verify location 1
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH);

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;
      expect(await oracle.isVerified(LOCATION_HASH_2)).to.be.false;

      // Verify location 2
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH_2, "copper", 2000, 7000, DATA_HASH);
      await oracle
        .connect(oracle3)
        .submitData(LOCATION_HASH_2, "copper", 2000, 8000, DATA_HASH);

      expect(await oracle.isVerified(LOCATION_HASH_2)).to.be.true;
    });
  });

  describe("Admin Functions", function () {
    it("should allow admin to update required confirmations", async function () {
      await expect(oracle.connect(admin).setRequiredConfirmations(3))
        .to.not.be.reverted;

      expect(await oracle.requiredConfirmations()).to.equal(3);
    });

    it("should reject setting required confirmations to 0", async function () {
      await expect(
        oracle.connect(admin).setRequiredConfirmations(0)
      ).to.be.revertedWith("Must require at least 1");
    });

    it("should reject non-admin from updating confirmations", async function () {
      await expect(
        oracle.connect(nonOracle).setRequiredConfirmations(3)
      ).to.be.reverted;
    });

    it("should apply new confirmation threshold to future submissions", async function () {
      await oracle.connect(admin).setRequiredConfirmations(3);

      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1000, 9000, DATA_HASH);

      // Still not verified (needs 3)
      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;

      // Third oracle triggers verification
      await oracle
        .connect(oracle3)
        .submitData(LOCATION_HASH, "gold", 1000, 8500, DATA_HASH);

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;
    });
  });

  describe("View Functions", function () {
    it("getSubmissions returns all submissions for a location", async function () {
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 1000, 8000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 1200, 9000, DATA_HASH);

      const subs = await oracle.getSubmissions(LOCATION_HASH);
      expect(subs.length).to.equal(2);
      expect(subs[0].oracle).to.equal(oracle1.address);
      expect(subs[1].oracle).to.equal(oracle2.address);
    });

    it("getSubmissions returns empty array for unknown location", async function () {
      const unknown = ethers.keccak256(ethers.toUtf8Bytes("nowhere"));
      const subs = await oracle.getSubmissions(unknown);
      expect(subs.length).to.equal(0);
    });

    it("isVerified returns false for unknown location", async function () {
      const unknown = ethers.keccak256(ethers.toUtf8Bytes("nowhere"));
      expect(await oracle.isVerified(unknown)).to.be.false;
    });

    it("getSubmissionCount returns 0 for unknown location", async function () {
      const unknown = ethers.keccak256(ethers.toUtf8Bytes("nowhere"));
      expect(await oracle.getSubmissionCount(unknown)).to.equal(0);
    });
  });

  describe("Full Oracle Flow", function () {
    it("should complete full flow: submit → consensus → verified", async function () {
      // Step 1: Oracle 1 submits data
      const tx1 = await oracle
        .connect(oracle1)
        .submitData(
          LOCATION_HASH,
          "ilmenite",
          ethers.parseEther("500"),
          8500,
          ethers.keccak256(ethers.toUtf8Bytes("data-1"))
        );
      const receipt1 = await tx1.wait();

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.false;
      expect(await oracle.getSubmissionCount(LOCATION_HASH)).to.equal(1);

      // Step 2: Oracle 2 submits data for same location
      const tx2 = await oracle
        .connect(oracle2)
        .submitData(
          LOCATION_HASH,
          "ilmenite",
          ethers.parseEther("500"),
          9000,
          ethers.keccak256(ethers.toUtf8Bytes("data-2"))
        );
      const receipt2 = await tx2.wait();

      // Step 3: Consensus reached — location verified
      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;

      // Step 4: Check all submissions are verified
      const subs = await oracle.getSubmissions(LOCATION_HASH);
      expect(subs.length).to.equal(2);
      expect(subs[0].verified).to.be.true;
      expect(subs[1].verified).to.be.true;

      // Step 5: Cannot submit more data to verified location
      await expect(
        oracle
          .connect(oracle3)
          .submitData(LOCATION_HASH, "ilmenite", 500, 8000, DATA_HASH)
      ).to.be.revertedWith("Already verified");
    });

    it("should handle different mineral types at different locations", async function () {
      // Location 1: Gold
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH, "gold", 5000, 9000, DATA_HASH);
      await oracle
        .connect(oracle2)
        .submitData(LOCATION_HASH, "gold", 5000, 8500, DATA_HASH);

      // Location 2: Copper
      await oracle
        .connect(oracle1)
        .submitData(LOCATION_HASH_2, "copper", 2000, 7500, DATA_HASH);
      await oracle
        .connect(oracle3)
        .submitData(LOCATION_HASH_2, "copper", 2000, 8000, DATA_HASH);

      expect(await oracle.isVerified(LOCATION_HASH)).to.be.true;
      expect(await oracle.isVerified(LOCATION_HASH_2)).to.be.true;

      const subs1 = await oracle.getSubmissions(LOCATION_HASH);
      const subs2 = await oracle.getSubmissions(LOCATION_HASH_2);

      expect(subs1[0].mineralType).to.equal("gold");
      expect(subs2[0].mineralType).to.equal("copper");
    });
  });
});
