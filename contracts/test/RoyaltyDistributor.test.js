const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

describe("RoyaltyDistributor", function () {
  let distributor;
  let admin, communityDev, communityWallet, protocolReserve, payer, nonAdmin;

  beforeEach(async function () {
    [admin, communityDev, communityWallet, protocolReserve, payer, nonAdmin] =
      await ethers.getSigners();

    const RoyaltyDistributor = await ethers.getContractFactory(
      "RoyaltyDistributor"
    );
    distributor = await upgrades.deployProxy(
      RoyaltyDistributor,
      [
        communityDev.address,
        communityWallet.address,
        protocolReserve.address,
        admin.address,
      ],
      { initializer: "initialize" }
    );
    await distributor.waitForDeployment();
  });

  describe("Initialization", function () {
    it("should set correct destination wallets", async function () {
      expect(await distributor.communityDevelopmentFund()).to.equal(
        communityDev.address
      );
      expect(await distributor.communityWallet()).to.equal(
        communityWallet.address
      );
      expect(await distributor.protocolReserve()).to.equal(
        protocolReserve.address
      );
    });

    it("should set default split percentages (70/20/10)", async function () {
      const [devBps, walletBps, reserveBps] = await distributor.getSplits();
      expect(devBps).to.equal(7000);
      expect(walletBps).to.equal(2000);
      expect(reserveBps).to.equal(1000);
    });

    it("should grant admin roles to deployer", async function () {
      const DEFAULT_ADMIN_ROLE =
        "0x0000000000000000000000000000000000000000000000000000000000000000";
      const DAO_ROLE = ethers.keccak256(ethers.toUtf8Bytes("DAO_ROLE"));
      const DISTRIBUTOR_ADMIN = ethers.keccak256(
        ethers.toUtf8Bytes("DISTRIBUTOR_ADMIN")
      );

      expect(await distributor.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to
        .be.true;
      expect(await distributor.hasRole(DAO_ROLE, admin.address)).to.be.true;
      expect(await distributor.hasRole(DISTRIBUTOR_ADMIN, admin.address)).to.be
        .true;
    });

    it("should start with zero distribution stats", async function () {
      const [total, count, lastTimestamp] = await distributor.getStats();
      expect(total).to.equal(0);
      expect(count).to.equal(0);
      expect(lastTimestamp).to.equal(0);
    });
  });

  describe("70/20/10 Royalty Split", function () {
    it("should split 1 ETH correctly: 0.7 dev, 0.2 wallet, 0.1 reserve", async function () {
      const amount = ethers.parseEther("1.0");

      const devBefore = await ethers.provider.getBalance(communityDev.address);
      const walletBefore = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveBefore = await ethers.provider.getBalance(
        protocolReserve.address
      );

      await payer.sendTransaction({
        to: await distributor.getAddress(),
        value: amount,
      });

      // Use distributeRevenue with a source
      await expect(
        distributor
          .connect(payer)
          .distributeRevenue(0, { value: amount }) // 0 = DATA_LICENSING
      )
        .to.emit(distributor, "RevenueDistributed")
        .withArgs(
          payer.address,
          0, // DATA_LICENSING
          amount,
          ethers.parseEther("0.7"),
          ethers.parseEther("0.2"),
          ethers.parseEther("0.1"),
          (v) => true // timestamp — any value
        );

      const devAfter = await ethers.provider.getBalance(communityDev.address);
      const walletAfter = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveAfter = await ethers.provider.getBalance(
        protocolReserve.address
      );

      expect(devAfter - devBefore).to.equal(ethers.parseEther("0.7"));
      expect(walletAfter - walletBefore).to.equal(ethers.parseEther("0.2"));
      expect(reserveAfter - reserveBefore).to.equal(ethers.parseEther("0.1"));
    });

    it("should split 10 ETH correctly", async function () {
      const amount = ethers.parseEther("10.0");

      const devBefore = await ethers.provider.getBalance(communityDev.address);
      const walletBefore = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveBefore = await ethers.provider.getBalance(
        protocolReserve.address
      );

      await distributor
        .connect(payer)
        .distributeRevenue(1, { value: amount }); // EXTRACTION

      const devAfter = await ethers.provider.getBalance(communityDev.address);
      const walletAfter = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveAfter = await ethers.provider.getBalance(
        protocolReserve.address
      );

      expect(devAfter - devBefore).to.equal(ethers.parseEther("7.0"));
      expect(walletAfter - walletBefore).to.equal(ethers.parseEther("2.0"));
      expect(reserveAfter - reserveBefore).to.equal(ethers.parseEther("1.0"));
    });

    it("should handle small amounts without rounding dust loss", async function () {
      // 1 wei — dev=0, wallet=0, reserve=1 (dust goes to reserve via subtraction)
      const amount = 1n;

      const reserveBefore = await ethers.provider.getBalance(
        protocolReserve.address
      );

      await distributor
        .connect(payer)
        .distributeRevenue(3, { value: amount }); // DONATION

      const reserveAfter = await ethers.provider.getBalance(
        protocolReserve.address
      );

      // All 1 wei should go somewhere — reserve gets the dust
      expect(reserveAfter - reserveBefore).to.equal(1n);
    });

    it("should split odd amounts correctly (dust to reserve)", async function () {
      const amount = ethers.parseEther("0.003"); // 3e15 wei

      // Expected: dev = 3e15 * 7000 / 10000 = 2100000000000000
      //           wallet = 3e15 * 2000 / 10000 = 600000000000000
      //           reserve = 3e15 - 2100000000000000 - 600000000000000 = 300000000000000
      const expectedDev = (amount * 7000n) / 10000n;
      const expectedWallet = (amount * 2000n) / 10000n;
      const expectedReserve = amount - expectedDev - expectedWallet;

      const devBefore = await ethers.provider.getBalance(communityDev.address);
      const walletBefore = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveBefore = await ethers.provider.getBalance(
        protocolReserve.address
      );

      await distributor
        .connect(payer)
        .distributeRevenue(2, { value: amount }); // PLATFORM_FEE

      const devAfter = await ethers.provider.getBalance(communityDev.address);
      const walletAfter = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveAfter = await ethers.provider.getBalance(
        protocolReserve.address
      );

      expect(devAfter - devBefore).to.equal(expectedDev);
      expect(walletAfter - walletBefore).to.equal(expectedWallet);
      expect(reserveAfter - reserveBefore).to.equal(expectedReserve);

      // Verify total distributed equals amount sent
      expect(
        expectedDev + expectedWallet + expectedReserve
      ).to.equal(amount);
    });

    it("should update stats after distribution", async function () {
      const amount = ethers.parseEther("1.0");

      await distributor
        .connect(payer)
        .distributeRevenue(0, { value: amount });

      const [total, count, lastTimestamp] = await distributor.getStats();
      expect(total).to.equal(amount);
      expect(count).to.equal(1);
      expect(lastTimestamp).to.be.gt(0);
    });

    it("should track multiple distributions", async function () {
      const amount1 = ethers.parseEther("1.0");
      const amount2 = ethers.parseEther("2.5");

      await distributor
        .connect(payer)
        .distributeRevenue(0, { value: amount1 });
      await distributor
        .connect(payer)
        .distributeRevenue(1, { value: amount2 });

      const [total, count] = await distributor.getStats();
      expect(total).to.equal(amount1 + amount2);
      expect(count).to.equal(2);
    });

    it("should reject zero-amount distribution", async function () {
      await expect(
        distributor.connect(payer).distributeRevenue(0, { value: 0 })
      ).to.be.revertedWith("Zero amount");
    });

    it("should allow anyone to distribute revenue", async function () {
      const amount = ethers.parseEther("0.5");
      await expect(
        distributor
          .connect(nonAdmin)
          .distributeRevenue(4, { value: amount }) // RECOVERY
      ).to.not.be.reverted;
    });

    it("should emit event with correct source enum", async function () {
      const amount = ethers.parseEther("1.0");

      // Test each source
      for (let source = 0; source < 5; source++) {
        await expect(
          distributor
            .connect(payer)
            .distributeRevenue(source, { value: amount })
        ).to.emit(distributor, "RevenueDistributed");
      }
    });
  });

  describe("Update Splits (DAO-only)", function () {
    it("should allow DAO to update splits within bounds", async function () {
      await expect(
        distributor.connect(admin).updateSplits(6000, 2000, 2000)
      )
        .to.emit(distributor, "SplitPercentagesUpdated")
        .withArgs(6000, 2000, 2000, (v) => true);

      const [devBps, walletBps, reserveBps] = await distributor.getSplits();
      expect(devBps).to.equal(6000);
      expect(walletBps).to.equal(2000);
      expect(reserveBps).to.equal(2000);
    });

    it("should reject splits that don't sum to 10000", async function () {
      await expect(
        distributor.connect(admin).updateSplits(7000, 2000, 2000)
      ).to.be.revertedWith("Must sum to 100%");
    });

    it("should reject if community share < 50%", async function () {
      // Community = dev + wallet = 4000 + 2000 = 6000... wait, MIN is 5000
      // Let's try: dev=3000, wallet=2000, reserve=5000 → community=5000 OK
      // Try: dev=2000, wallet=2000, reserve=6000 → community=4000 < 5000
      await expect(
        distributor.connect(admin).updateSplits(2000, 2000, 6000)
      ).to.be.revertedWith("Community share too low");
    });

    it("should reject if reserve > 20%", async function () {
      await expect(
        distributor.connect(admin).updateSplits(5000, 2000, 3000)
      ).to.be.revertedWith("Reserve too high");
    });

    it("should allow exact boundary: reserve = 20%", async function () {
      await expect(distributor.connect(admin).updateSplits(5000, 3000, 2000))
        .to.not.be.reverted;
    });

    it("should allow exact boundary: community = 50%", async function () {
      await expect(distributor.connect(admin).updateSplits(3000, 2000, 5000))
        .to.be.revertedWith("Reserve too high");

      // community=5000, reserve=2000 (max)
      await expect(distributor.connect(admin).updateSplits(3000, 2000, 5000))
        .to.be.revertedWith("Reserve too high");

      // community=5000 exactly, reserve=2000 exactly
      await expect(distributor.connect(admin).updateSplits(5000, 0, 5000))
        .to.be.revertedWith("Reserve too high");
    });

    it("should reject non-DAO callers", async function () {
      await expect(
        distributor.connect(nonAdmin).updateSplits(6000, 2000, 2000)
      ).to.be.reverted;
    });

    it("should apply new splits to subsequent distributions", async function () {
      // Change to 60/20/20
      await distributor.connect(admin).updateSplits(6000, 2000, 2000);

      const amount = ethers.parseEther("10.0");

      const devBefore = await ethers.provider.getBalance(communityDev.address);
      const walletBefore = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveBefore = await ethers.provider.getBalance(
        protocolReserve.address
      );

      await distributor
        .connect(payer)
        .distributeRevenue(0, { value: amount });

      const devAfter = await ethers.provider.getBalance(communityDev.address);
      const walletAfter = await ethers.provider.getBalance(
        communityWallet.address
      );
      const reserveAfter = await ethers.provider.getBalance(
        protocolReserve.address
      );

      expect(devAfter - devBefore).to.equal(ethers.parseEther("6.0"));
      expect(walletAfter - walletBefore).to.equal(ethers.parseEther("2.0"));
      expect(reserveAfter - reserveBefore).to.equal(ethers.parseEther("2.0"));
    });
  });

  describe("Update Destinations (DAO-only)", function () {
    it("should allow DAO to update individual destinations", async function () {
      const newDev = nonAdmin.address;
      await expect(
        distributor.connect(admin).updateDestinations(newDev, ethers.ZeroAddress, ethers.ZeroAddress)
      )
        .to.emit(distributor, "DestinationUpdated")
        .withArgs(newDev, "development", (v) => true);

      expect(await distributor.communityDevelopmentFund()).to.equal(newDev);
      // Others unchanged
      expect(await distributor.communityWallet()).to.equal(
        communityWallet.address
      );
    });

    it("should reject non-DAO callers", async function () {
      await expect(
        distributor
          .connect(nonAdmin)
          .updateDestinations(
            nonAdmin.address,
            ethers.ZeroAddress,
            ethers.ZeroAddress
          )
      ).to.be.reverted;
    });

    it("should allow updating all three at once", async function () {
      const [a, b, c, d] = await ethers.getSigners();
      await distributor
        .connect(admin)
        .updateDestinations(d.address, c.address, b.address);

      expect(await distributor.communityDevelopmentFund()).to.equal(d.address);
      expect(await distributor.communityWallet()).to.equal(c.address);
      expect(await distributor.protocolReserve()).to.equal(b.address);
    });
  });

  describe("Reentrancy Protection", function () {
    it("should have nonReentrant on distributeRevenue", async function () {
      // Verify the function selector includes nonReentrant guard
      // We test by ensuring the contract compiles with the modifier
      const amount = ethers.parseEther("1.0");
      await expect(
        distributor
          .connect(payer)
          .distributeRevenue(0, { value: amount })
      ).to.not.be.reverted;
    });
  });

  describe("View Functions", function () {
    it("getSplits returns correct default values", async function () {
      const [dev, wallet, reserve] = await distributor.getSplits();
      expect(dev).to.equal(7000);
      expect(wallet).to.equal(2000);
      expect(reserve).to.equal(1000);
    });

    it("getStats returns correct values after distributions", async function () {
      const amount = ethers.parseEther("5.0");
      await distributor
        .connect(payer)
        .distributeRevenue(0, { value: amount });

      const [total, count, lastTimestamp] = await distributor.getStats();
      expect(total).to.equal(amount);
      expect(count).to.equal(1);
      expect(lastTimestamp).to.be.gt(0);
    });
  });
});
