const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("QuadraticVoting", function () {
  let governanceToken, voting;
  let admin, voter1, voter2, voter3, whale, other;

  const PRECISION = ethers.parseEther("1"); // 1e18
  const MINIMUM_TOKENS = ethers.parseEther("1");
  const PROPOSAL_ID = 1;

  // Helper: compute expected quadratic power = sqrt(tokens * 1e18)
  function expectedQuadraticPower(tokensStr) {
    const tokens = BigInt(tokensStr);
    const product = tokens * PRECISION;
    // Integer sqrt
    if (product === 0n) return 0n;
    let z = (product + 1n) / 2n;
    let y = product;
    while (z < y) {
      y = z;
      z = (product / z + z) / 2n;
    }
    return y;
  }

  beforeEach(async function () {
    [admin, voter1, voter2, voter3, whale, other] = await ethers.getSigners();

    // Deploy a mock ERC20 token for governance
    const MockToken = await ethers.getContractFactory("GovernanceToken");
    governanceToken = await MockToken.deploy();
    await governanceToken.waitForDeployment();

    // Deploy QuadraticVoting
    const QuadraticVoting = await ethers.getContractFactory("QuadraticVoting");
    voting = await QuadraticVoting.deploy(await governanceToken.getAddress());
    await voting.waitForDeployment();

    // Mint tokens to voters
    await governanceToken.mint(voter1.address, ethers.parseEther("1000"));
    await governanceToken.mint(voter2.address, ethers.parseEther("1000"));
    await governanceToken.mint(voter3.address, ethers.parseEther("1000"));
    await governanceToken.mint(whale.address, ethers.parseEther("1000000")); // 1M tokens

    // Approve voting contract to spend tokens
    await governanceToken
      .connect(voter1)
      .approve(await voting.getAddress(), ethers.MaxUint256);
    await governanceToken
      .connect(voter2)
      .approve(await voting.getAddress(), ethers.MaxUint256);
    await governanceToken
      .connect(voter3)
      .approve(await voting.getAddress(), ethers.MaxUint256);
    await governanceToken
      .connect(whale)
      .approve(await voting.getAddress(), ethers.MaxUint256);
  });

  describe("Quadratic Voting Math", function () {
    it("should compute sqrt(1 token) = 1 vote power", async function () {
      const tokens = ethers.parseEther("1"); // 1e18
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      // sqrt(1e18 * 1e18) = sqrt(1e36) = 1e18
      expect(vote.quadraticPower).to.equal(PRECISION); // 1 vote
    });

    it("should compute sqrt(4 tokens) = 2 vote power", async function () {
      const tokens = ethers.parseEther("4");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      // sqrt(4e18 * 1e18) = sqrt(4e36) = 2e18
      expect(vote.quadraticPower).to.equal(PRECISION * 2n); // 2 votes
    });

    it("should compute sqrt(9 tokens) = 3 vote power", async function () {
      const tokens = ethers.parseEther("9");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.quadraticPower).to.equal(PRECISION * 3n); // 3 votes
    });

    it("should compute sqrt(100 tokens) = 10 vote power", async function () {
      const tokens = ethers.parseEther("100");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.quadraticPower).to.equal(PRECISION * 10n); // 10 votes
    });

    it("should compute sqrt(10000 tokens) = 100 vote power", async function () {
      const tokens = ethers.parseEther("10000");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.quadraticPower).to.equal(PRECISION * 100n); // 100 votes
    });

    it("should compute sqrt(1000000 tokens) = 1000 vote power", async function () {
      const tokens = ethers.parseEther("1000000");
      await voting.connect(whale).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, whale.address);
      expect(vote.quadraticPower).to.equal(PRECISION * 1000n); // 1000 votes
    });

    it("demonstrates quadratic dampening: 1M tokens = 1000x power (not 1M)", async function () {
      // This is the core anti-plutocracy mechanism
      const whaleTokens = ethers.parseEther("1000000"); // 1M tokens
      const smallTokens = ethers.parseEther("1"); // 1 token

      await voting.connect(whale).castVote(PROPOSAL_ID, whaleTokens, true);
      await voting.connect(voter1).castVote(PROPOSAL_ID + 1, smallTokens, true);

      const whaleVote = await voting.getVote(PROPOSAL_ID, whale.address);
      const smallVote = await voting.getVote(PROPOSAL_ID + 1, voter1.address);

      // Whale has 1Mx tokens but only 1000x voting power
      const tokenRatio = whaleTokens / smallTokens; // 1,000,000
      const powerRatio = whaleVote.quadraticPower / smallVote.quadraticPower; // 1,000

      expect(tokenRatio).to.equal(1000000n);
      expect(powerRatio).to.equal(1000n);
      // 1000x power from 1Mx tokens = sqrt dampening confirmed
    });
  });

  describe("Cast Vote", function () {
    it("should lock tokens in contract", async function () {
      const tokens = ethers.parseEther("100");

      const balanceBefore = await governanceToken.balanceOf(voter1.address);
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);
      const balanceAfter = await governanceToken.balanceOf(voter1.address);

      expect(balanceBefore - balanceAfter).to.equal(tokens);
      expect(
        await governanceToken.balanceOf(await voting.getAddress())
      ).to.equal(tokens);
    });

    it("should record vote details correctly", async function () {
      const tokens = ethers.parseEther("100");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.proposalId).to.equal(PROPOSAL_ID);
      expect(vote.voter).to.equal(voter1.address);
      expect(vote.tokensCommitted).to.equal(tokens);
      expect(vote.quadraticPower).to.equal(PRECISION * 10n);
      expect(vote.support).to.be.true;
      expect(vote.timestamp).to.be.gt(0);
    });

    it("should update totals for 'for' votes", async function () {
      const tokens = ethers.parseEther("100");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      const [forPower, againstPower, totalVoters, totalLocked] =
        await voting.getVoteResults(PROPOSAL_ID);

      expect(forPower).to.equal(PRECISION * 10n);
      expect(againstPower).to.equal(0);
      expect(totalVoters).to.equal(1);
      expect(totalLocked).to.equal(tokens);
    });

    it("should update totals for 'against' votes", async function () {
      const tokens = ethers.parseEther("100");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, false);

      const [forPower, againstPower] = await voting.getVoteResults(
        PROPOSAL_ID
      );

      expect(forPower).to.equal(0);
      expect(againstPower).to.equal(PRECISION * 10n);
    });

    it("should aggregate multiple votes correctly", async function () {
      // voter1: 100 tokens → 10 power (for)
      // voter2: 400 tokens → 20 power (for)
      // voter3: 900 tokens → 30 power (against)
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), true);
      await voting
        .connect(voter2)
        .castVote(PROPOSAL_ID, ethers.parseEther("400"), true);
      await voting
        .connect(voter3)
        .castVote(PROPOSAL_ID, ethers.parseEther("900"), false);

      const [forPower, againstPower, totalVoters, totalLocked] =
        await voting.getVoteResults(PROPOSAL_ID);

      expect(forPower).to.equal(PRECISION * 30n); // 10 + 20
      expect(againstPower).to.equal(PRECISION * 30n); // 30
      expect(totalVoters).to.equal(3);
      expect(totalLocked).to.equal(
        ethers.parseEther("1400") // 100 + 400 + 900
      );
    });

    it("should set unlock time to 7 days after vote", async function () {
      const tokens = ethers.parseEther("10");
      const tx = await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, tokens, true);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);

      const unlock = await voting.unlockTime(PROPOSAL_ID, voter1.address);
      // VOTE_LOCK_DURATION = 7 days = 604800 seconds
      expect(unlock).to.equal(block.timestamp + 604800);
    });

    it("should emit VoteCast event", async function () {
      const tokens = ethers.parseEther("100");
      await expect(
        voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true)
      )
        .to.emit(voting, "VoteCast")
        .withArgs(
          PROPOSAL_ID,
          voter1.address,
          tokens,
          PRECISION * 10n,
          true
        );
    });

    it("should reject votes below minimum tokens", async function () {
      const belowMin = ethers.parseEther("0.5");
      await expect(
        voting.connect(voter1).castVote(PROPOSAL_ID, belowMin, true)
      ).to.be.revertedWith("Below minimum tokens");
    });

    it("should reject duplicate votes on same proposal", async function () {
      const tokens = ethers.parseEther("100");
      await voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true);

      await expect(
        voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true)
      ).to.be.revertedWith("Already voted on this proposal");
    });

    it("should allow same voter to vote on different proposals", async function () {
      const tokens = ethers.parseEther("100");

      await expect(
        voting.connect(voter1).castVote(1, tokens, true)
      ).to.not.be.reverted;
      await expect(
        voting.connect(voter1).castVote(2, tokens, true)
      ).to.not.be.reverted;
    });
  });

  describe("Withdraw Vote", function () {
    const VOTE_LOCK_DURATION = 604800; // 7 days in seconds

    beforeEach(async function () {
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), true);
    });

    it("should reject withdrawal before lock expires", async function () {
      await expect(
        voting.connect(voter1).withdrawVote(PROPOSAL_ID)
      ).to.be.revertedWith("Tokens still locked");
    });

    it("should return tokens after lock expires", async function () {
      // Fast forward 7 days
      await ethers.provider.send("evm_increaseTime", [VOTE_LOCK_DURATION]);
      await ethers.provider.send("evm_mine", []);

      const balanceBefore = await governanceToken.balanceOf(voter1.address);
      await voting.connect(voter1).withdrawVote(PROPOSAL_ID);
      const balanceAfter = await governanceToken.balanceOf(voter1.address);

      expect(balanceAfter - balanceBefore).to.equal(ethers.parseEther("100"));
    });

    it("should emit VoteWithdrawn event", async function () {
      await ethers.provider.send("evm_increaseTime", [VOTE_LOCK_DURATION]);
      await ethers.provider.send("evm_mine", []);

      await expect(voting.connect(voter1).withdrawVote(PROPOSAL_ID))
        .to.emit(voting, "VoteWithdrawn")
        .withArgs(PROPOSAL_ID, voter1.address, ethers.parseEther("100"));
    });

    it("should clear vote data after withdrawal", async function () {
      await ethers.provider.send("evm_increaseTime", [VOTE_LOCK_DURATION]);
      await ethers.provider.send("evm_mine", []);

      await voting.connect(voter1).withdrawVote(PROPOSAL_ID);

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.tokensCommitted).to.equal(0);
    });

    it("should update totalTokensLocked after withdrawal", async function () {
      // Add another voter
      await voting
        .connect(voter2)
        .castVote(PROPOSAL_ID, ethers.parseEther("200"), true);

      expect(await voting.totalTokensLocked(PROPOSAL_ID)).to.equal(
        ethers.parseEther("300")
      );

      await ethers.provider.send("evm_increaseTime", [VOTE_LOCK_DURATION]);
      await ethers.provider.send("evm_mine", []);

      await voting.connect(voter1).withdrawVote(PROPOSAL_ID);

      expect(await voting.totalTokensLocked(PROPOSAL_ID)).to.equal(
        ethers.parseEther("200")
      );
    });

    it("should reject withdrawal with no vote", async function () {
      await ethers.provider.send("evm_increaseTime", [VOTE_LOCK_DURATION]);
      await ethers.provider.send("evm_mine", []);

      await expect(
        voting.connect(other).withdrawVote(PROPOSAL_ID)
      ).to.be.revertedWith("No vote to withdraw");
    });
  });

  describe("Proposal Results & Passing", function () {
    it("should report proposal as passed with >50% for power", async function () {
      // voter1: 100 tokens → 10 power (for)
      // voter2: 100 tokens → 10 power (against)
      // voter3: 400 tokens → 20 power (for)
      // Total for: 30, against: 10 → passed
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), true);
      await voting
        .connect(voter2)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), false);
      await voting
        .connect(voter3)
        .castVote(PROPOSAL_ID, ethers.parseEther("400"), true);

      expect(await voting.hasProposalPassed(PROPOSAL_ID)).to.be.true;
    });

    it("should report proposal as failed with ≤50% for power", async function () {
      // voter1: 100 tokens → 10 power (for)
      // voter2: 100 tokens → 10 power (against)
      // Tied → not passed
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), true);
      await voting
        .connect(voter2)
        .castVote(PROPOSAL_ID, ethers.parseEther("100"), false);

      expect(await voting.hasProposalPassed(PROPOSAL_ID)).to.be.false;
    });

    it("should require minimum participation (100 * PRECISION total power)", async function () {
      // Only 1 token = 1 power → below 100 threshold
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("1"), true);

      expect(await voting.hasProposalPassed(PROPOSAL_ID)).to.be.false;
    });

    it("should pass with enough participation and majority", async function () {
      // Need total power >= 100 * PRECISION
      // voter1: 10000 tokens → 100 power (for)
      // voter2: 10000 tokens → 100 power (for)
      // Total for: 200, against: 0 → passed, participation: 200 >= 100
      await voting
        .connect(voter1)
        .castVote(PROPOSAL_ID, ethers.parseEther("10000"), true);
      await voting
        .connect(voter2)
        .castVote(PROPOSAL_ID, ethers.parseEther("10000"), true);

      expect(await voting.hasProposalPassed(PROPOSAL_ID)).to.be.true;
    });

    it("should return false for proposal with no votes", async function () {
      expect(await voting.hasProposalPassed(999)).to.be.false;
    });
  });

  describe("Access Control", function () {
    it("should grant admin roles to deployer", async function () {
      const DEFAULT_ADMIN_ROLE =
        "0x0000000000000000000000000000000000000000000000000000000000000000";
      const VOTING_ADMIN = ethers.keccak256(
        ethers.toUtf8Bytes("VOTING_ADMIN")
      );

      expect(await voting.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be
        .true;
      expect(await voting.hasRole(VOTING_ADMIN, admin.address)).to.be.true;
    });

    it("should expose governance token address", async function () {
      expect(await voting.governanceToken()).to.equal(
        await governanceToken.getAddress()
      );
    });
  });

  describe("Edge Cases", function () {
    it("should handle exact minimum token vote", async function () {
      const tokens = ethers.parseEther("1");
      await expect(
        voting.connect(voter1).castVote(PROPOSAL_ID, tokens, true)
      ).to.not.be.reverted;

      const vote = await voting.getVote(PROPOSAL_ID, voter1.address);
      expect(vote.quadraticPower).to.equal(PRECISION); // sqrt(1) = 1
    });

    it("should handle very large token amounts", async function () {
      const tokens = ethers.parseEther("1000000"); // 1M
      await voting.connect(whale).castVote(PROPOSAL_ID, tokens, true);

      const vote = await voting.getVote(PROPOSAL_ID, whale.address);
      expect(vote.quadraticPower).to.equal(PRECISION * 1000n); // sqrt(1M) = 1000
    });

    it("should correctly track multiple proposals independently", async function () {
      await voting
        .connect(voter1)
        .castVote(1, ethers.parseEther("100"), true);
      await voting
        .connect(voter1)
        .castVote(2, ethers.parseEther("400"), false);

      const vote1 = await voting.getVote(1, voter1.address);
      const vote2 = await voting.getVote(2, voter1.address);

      expect(vote1.support).to.be.true;
      expect(vote2.support).to.be.false;
      expect(vote1.quadraticPower).to.equal(PRECISION * 10n);
      expect(vote2.quadraticPower).to.equal(PRECISION * 20n);

      const [for1, against1] = await voting.getVoteResults(1);
      const [for2, against2] = await voting.getVoteResults(2);

      expect(for1).to.equal(PRECISION * 10n);
      expect(against1).to.equal(0);
      expect(for2).to.equal(0);
      expect(against2).to.equal(PRECISION * 20n);
    });
  });
});
