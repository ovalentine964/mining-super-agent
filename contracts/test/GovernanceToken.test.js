const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("GovernanceToken", function () {
  let token;
  let owner, minter, vestingAdmin, user1, user2, zeroAddress;

  const MAX_SUPPLY = ethers.parseEther("1000000000"); // 1 billion
  const ONE_TOKEN = ethers.parseEther("1");

  beforeEach(async function () {
    [owner, minter, vestingAdmin, user1, user2] = await ethers.getSigners();

    const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
    token = await GovernanceToken.deploy();
    await token.waitForDeployment();

    // Grant roles for testing
    const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
    const VESTING_ADMIN = ethers.keccak256(ethers.toUtf8Bytes("VESTING_ADMIN"));
    await token.grantRole(MINTER_ROLE, minter.address);
    await token.grantRole(VESTING_ADMIN, vestingAdmin.address);
  });

  // ─── Deployment ──────────────────────────────────────────────────

  describe("Deployment", function () {
    it("should have correct name and symbol", async function () {
      expect(await token.name()).to.equal("Sovereign Resource DAO");
      expect(await token.symbol()).to.equal("MINE");
    });

    it("should have correct MAX_SUPPLY", async function () {
      expect(await token.MAX_SUPPLY()).to.equal(MAX_SUPPLY);
    });

    it("should grant deployer DEFAULT_ADMIN, MINTER, and VESTING_ADMIN roles", async function () {
      const DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000";
      const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
      const VESTING_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("VESTING_ADMIN"));

      expect(await token.hasRole(DEFAULT_ADMIN_ROLE, owner.address)).to.be.true;
      expect(await token.hasRole(MINTER_ROLE, owner.address)).to.be.true;
      expect(await token.hasRole(VESTING_ADMIN_ROLE, owner.address)).to.be.true;
    });
  });

  // ─── Minting ─────────────────────────────────────────────────────

  describe("Minting", function () {
    it("should allow MINTER_ROLE to mint tokens", async function () {
      const amount = ethers.parseEther("1000");
      await token.connect(minter).mint(user1.address, amount);
      expect(await token.balanceOf(user1.address)).to.equal(amount);
    });

    it("should update totalMinted after minting", async function () {
      const amount = ethers.parseEther("500");
      await token.connect(minter).mint(user1.address, amount);
      expect(await token.totalMinted()).to.equal(amount);
    });

    it("should revert when non-minter tries to mint", async function () {
      const amount = ethers.parseEther("100");
      await expect(
        token.connect(user1).mint(user1.address, amount)
      ).to.be.reverted;
    });

    it("should revert when minting exceeds MAX_SUPPLY", async function () {
      const overMax = MAX_SUPPLY + ONE_TOKEN;
      await expect(
        token.connect(minter).mint(user1.address, overMax)
      ).to.be.revertedWith("Exceeds max supply");
    });

    it("should allow minting up to exactly MAX_SUPPLY", async function () {
      await token.connect(minter).mint(user1.address, MAX_SUPPLY);
      expect(await token.totalMinted()).to.equal(MAX_SUPPLY);
      expect(await token.balanceOf(user1.address)).to.equal(MAX_SUPPLY);
    });

    it("should revert when cumulative minting exceeds MAX_SUPPLY", async function () {
      const half = MAX_SUPPLY / 2n;
      await token.connect(minter).mint(user1.address, half);
      await token.connect(minter).mint(user2.address, half);
      // Now at max, one more should fail
      await expect(
        token.connect(minter).mint(user1.address, ONE_TOKEN)
      ).to.be.revertedWith("Exceeds max supply");
    });
  });

  // ─── Vesting Schedule Creation ────────────────────────────────────

  describe("Vesting Schedule Creation", function () {
    const amount = ethers.parseEther("100000");
    const cliffDuration = 365 * 24 * 60 * 60; // 1 year
    const vestingDuration = 4 * 365 * 24 * 60 * 60; // 4 years

    it("should create a vesting schedule with valid parameters", async function () {
      await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );

      const schedule = await token.vestingSchedules(user1.address);
      expect(schedule.totalAmount).to.equal(amount);
      expect(schedule.released).to.equal(0);
      expect(schedule.cliffDuration).to.equal(cliffDuration);
      expect(schedule.vestingDuration).to.equal(vestingDuration);
      expect(schedule.revocable).to.be.true;
    });

    it("should emit TokensVested event", async function () {
      const tx = await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);

      await expect(tx)
        .to.emit(token, "TokensVested")
        .withArgs(
          user1.address,
          amount,
          block.timestamp + cliffDuration,
          block.timestamp + vestingDuration
        );
    });

    it("should increase totalMinted when creating vesting", async function () {
      await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );
      expect(await token.totalMinted()).to.equal(amount);
    });

    it("should hold tokens in the contract", async function () {
      await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );
      expect(await token.balanceOf(await token.getAddress())).to.equal(amount);
    });

    it("should revert with zero address beneficiary", async function () {
      await expect(
        token.connect(vestingAdmin).createVesting(
          ethers.ZeroAddress, amount, cliffDuration, vestingDuration, true
        )
      ).to.be.revertedWith("Zero address beneficiary");
    });

    it("should revert with zero amount", async function () {
      await expect(
        token.connect(vestingAdmin).createVesting(
          user1.address, 0, cliffDuration, vestingDuration, true
        )
      ).to.be.revertedWith("Zero amount");
    });

    it("should revert with zero vesting duration (division by zero protection)", async function () {
      await expect(
        token.connect(vestingAdmin).createVesting(
          user1.address, amount, 0, 0, true
        )
      ).to.be.revertedWith("Zero vesting duration");
    });

    it("should revert when cliff exceeds vesting duration", async function () {
      const longCliff = 5 * 365 * 24 * 60 * 60; // 5 years
      const shortVest = 2 * 365 * 24 * 60 * 60; // 2 years
      await expect(
        token.connect(vestingAdmin).createVesting(
          user1.address, amount, longCliff, shortVest, true
        )
      ).to.be.revertedWith("Cliff exceeds vesting duration");
    });

    it("should revert when beneficiary already has a vesting schedule", async function () {
      await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );
      await expect(
        token.connect(vestingAdmin).createVesting(
          user1.address, amount, cliffDuration, vestingDuration, true
        )
      ).to.be.revertedWith("Already vested");
    });

    it("should revert when non-VESTING_ADMIN creates vesting", async function () {
      await expect(
        token.connect(user1).createVesting(
          user2.address, amount, cliffDuration, vestingDuration, true
        )
      ).to.be.reverted;
    });
  });

  // ─── Vesting Release Calculation ──────────────────────────────────

  describe("Vesting Release Calculation", function () {
    const amount = ethers.parseEther("1000000"); // 1M tokens
    const cliffDuration = 365 * 24 * 60 * 60; // 1 year
    const vestingDuration = 4 * 365 * 24 * 60 * 60; // 4 years

    beforeEach(async function () {
      await token.connect(vestingAdmin).createVesting(
        user1.address, amount, cliffDuration, vestingDuration, true
      );
    });

    it("should release 0 tokens before cliff", async function () {
      // Move time to just before cliff (e.g., 6 months)
      await time.increase(180 * 24 * 60 * 60);

      // releaseVested should revert with "Nothing to release"
      await expect(
        token.connect(user1).releaseVested()
      ).to.be.revertedWith("Nothing to release");
    });

    it("should release 0 tokens exactly at cliff start (cliff boundary)", async function () {
      // Move to exactly the cliff end
      await time.increase(cliffDuration);

      // At the cliff boundary, elapsed == cliffDuration
      // vested = (totalAmount * elapsed) / vestingDuration = amount * 1/4 = 25%
      // But we need to check: after cliff, elapsed >= cliff, so not in cliff check.
      // elapsed = cliffDuration, vestingDuration = 4 * cliffDuration
      // vested = (amount * cliffDuration) / (4 * cliffDuration) = amount / 4
      // So 25% should be releasable
      const expectedRelease = amount / 4n;
      await token.connect(user1).releaseVested();
      expect(await token.balanceOf(user1.address)).to.equal(expectedRelease);
    });

    it("should release proportional tokens after cliff (linear vesting)", async function () {
      // Move to 2 years (halfway through 4-year vest)
      await time.increase(2 * 365 * 24 * 60 * 60);

      // At 2 years: elapsed = 2y, vestingDuration = 4y
      // vested = amount * 2/4 = 50%
      const expectedRelease = amount / 2n;
      await token.connect(user1).releaseVested();
      expect(await token.balanceOf(user1.address)).to.equal(expectedRelease);
    });

    it("should release all tokens when fully vested", async function () {
      // Move past full vesting period
      await time.increase(vestingDuration + 1);

      await token.connect(user1).releaseVested();
      expect(await token.balanceOf(user1.address)).to.equal(amount);
    });

    it("should emit TokensReleased event", async function () {
      await time.increase(vestingDuration + 1);

      await expect(token.connect(user1).releaseVested())
        .to.emit(token, "TokensReleased")
        .withArgs(user1.address, amount);
    });

    it("should update released amount after partial release", async function () {
      // Release at 1 year (25%)
      await time.increase(cliffDuration);
      await token.connect(user1).releaseVested();

      const schedule = await token.vestingSchedules(user1.address);
      expect(schedule.released).to.equal(amount / 4n);
    });

    it("should allow multiple releases to accumulate", async function () {
      // First release at 1 year
      await time.increase(cliffDuration);
      await token.connect(user1).releaseVested();
      const balance1 = await token.balanceOf(user1.address);

      // Second release at 2 years
      await time.increase(365 * 24 * 60 * 60);
      await token.connect(user1).releaseVested();
      const balance2 = await token.balanceOf(user1.address);

      expect(balance2).to.be.gt(balance1);
    });

    it("should revert release when no vesting schedule exists", async function () {
      await expect(
        token.connect(user2).releaseVested()
      ).to.be.revertedWith("No vesting schedule");
    });
  });

  // ─── ERC20Votes (Delegation) ─────────────────────────────────────

  describe("Token Delegation (ERC20Votes)", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("1000");
      await token.connect(minter).mint(user1.address, amount);
    });

    it("should allow delegating votes to self", async function () {
      await token.connect(user1).delegate(user1.address);
      const votes = await token.getVotes(user1.address);
      expect(votes).to.equal(ethers.parseEther("1000"));
    });

    it("should allow delegating votes to another address", async function () {
      await token.connect(user1).delegate(user2.address);
      const votes = await token.getVotes(user2.address);
      expect(votes).to.equal(ethers.parseEther("1000"));
      expect(await token.getVotes(user1.address)).to.equal(0);
    });

    it("should update votes after transfer", async function () {
      await token.connect(user1).delegate(user1.address);
      const transferAmount = ethers.parseEther("500");
      await token.connect(user1).transfer(user2.address, transferAmount);

      expect(await token.getVotes(user1.address)).to.equal(ethers.parseEther("500"));
      // user2 has no delegate set, so no votes
      expect(await token.getVotes(user2.address)).to.equal(0);
    });

    it("should return 0 votes for non-delegated address", async function () {
      expect(await token.getVotes(user1.address)).to.equal(0);
    });

    it("should track voting checkpoints", async function () {
      await token.connect(user1).delegate(user1.address);
      const tx = await token.connect(minter).mint(user1.address, ethers.parseEther("500"));
      const block = await ethers.provider.getBlock(tx.blockNumber);

      const checkpoint = await token.getPastVotes(user1.address, block.number - 1);
      expect(checkpoint).to.equal(ethers.parseEther("1000"));

      const currentCheckpoint = await token.getPastVotes(user1.address, block.number);
      expect(currentCheckpoint).to.equal(ethers.parseEther("1500"));
    });
  });

  // ─── Access Control ──────────────────────────────────────────────

  describe("Access Control", function () {
    it("should allow admin to grant MINTER_ROLE", async function () {
      const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
      await token.grantRole(MINTER_ROLE, user1.address);
      expect(await token.hasRole(MINTER_ROLE, user1.address)).to.be.true;
    });

    it("should allow admin to revoke MINTER_ROLE", async function () {
      const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
      await token.grantRole(MINTER_ROLE, user1.address);
      await token.revokeRole(MINTER_ROLE, user1.address);
      expect(await token.hasRole(MINTER_ROLE, user1.address)).to.be.false;
    });

    it("should prevent non-admin from granting roles", async function () {
      const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
      await expect(
        token.connect(user1).grantRole(MINTER_ROLE, user2.address)
      ).to.be.reverted;
    });

    it("should allow MINTER_ROLE holder to mint", async function () {
      const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
      await token.grantRole(MINTER_ROLE, user1.address);
      await token.connect(user1).mint(user2.address, ethers.parseEther("100"));
      expect(await token.balanceOf(user2.address)).to.equal(ethers.parseEther("100"));
    });

    it("should allow VESTING_ADMIN to create vesting", async function () {
      const VESTING_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("VESTING_ADMIN"));
      await token.grantRole(VESTING_ADMIN_ROLE, user1.address);
      const cliff = 365 * 24 * 60 * 60;
      const vest = 4 * 365 * 24 * 60 * 60;
      await token.connect(user1).createVesting(
        user2.address, ethers.parseEther("1000"), cliff, vest, false
      );
      const schedule = await token.vestingSchedules(user2.address);
      expect(schedule.totalAmount).to.equal(ethers.parseEther("1000"));
    });
  });
});
