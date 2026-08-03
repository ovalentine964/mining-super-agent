/**
 * Sovereign Resource DAO — Deployment Script
 *
 * Deploys all smart contracts to Polygon (Mumbai testnet or mainnet).
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network mumbai    (testnet)
 *   npx hardhat run scripts/deploy.js --network polygon   (mainnet)
 */

const { ethers, upgrades } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  // ── 1. Deploy Governance Token ($MINE) ──────────────────────────
  console.log("\n1. Deploying GovernanceToken ($MINE)...");
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
  const token = await GovernanceToken.deploy();
  await token.waitForDeployment();
  console.log("   GovernanceToken deployed to:", await token.getAddress());

  // ── 2. Deploy RoyaltyDistributor (UUPS Proxy) ───────────────────
  console.log("\n2. Deploying RoyaltyDistributor (proxy)...");
  const RoyaltyDistributor = await ethers.getContractFactory("RoyaltyDistributor");
  const devFund = deployer.address;    // Replace with actual dev fund address
  const communityWallet = deployer.address; // Replace with actual community wallet
  const reserve = deployer.address;    // Replace with actual reserve address

  const distributor = await upgrades.deployProxy(
    RoyaltyDistributor,
    [devFund, communityWallet, reserve, deployer.address],
    { initializer: "initialize" }
  );
  await distributor.waitForDeployment();
  console.log("   RoyaltyDistributor deployed to:", await distributor.getAddress());

  // ── 3. Deploy ExtractionTracker ─────────────────────────────────
  console.log("\n3. Deploying ExtractionTracker...");
  const ExtractionTracker = await ethers.getContractFactory("ExtractionTracker");
  const tracker = await ExtractionTracker.deploy();
  await tracker.waitForDeployment();
  console.log("   ExtractionTracker deployed to:", await tracker.getAddress());

  // ── 4. Deploy MiningOracle ──────────────────────────────────────
  console.log("\n4. Deploying MiningOracle...");
  const MiningOracle = await ethers.getContractFactory("MiningOracle");
  const oracle = await MiningOracle.deploy();
  await oracle.waitForDeployment();
  console.log("   MiningOracle deployed to:", await oracle.getAddress());

  // ── 5. Deploy QuadraticVoting ───────────────────────────────────
  console.log("\n5. Deploying QuadraticVoting...");
  const QuadraticVoting = await ethers.getContractFactory("QuadraticVoting");
  const voting = await QuadraticVoting.deploy(await token.getAddress());
  await voting.waitForDeployment();
  console.log("   QuadraticVoting deployed to:", await voting.getAddress());

  // ── Summary ─────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("SOVEREIGN RESOURCE DAO — DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log({
    GovernanceToken: await token.getAddress(),
    RoyaltyDistributor: await distributor.getAddress(),
    ExtractionTracker: await tracker.getAddress(),
    MiningOracle: await oracle.getAddress(),
    QuadraticVoting: await voting.getAddress(),
  });
  console.log("=".repeat(60));

  // Save deployment addresses
  const fs = require("fs");
  const addresses = {
    network: (await deployer.provider.getNetwork()).name,
    chainId: (await deployer.provider.getNetwork()).chainId.toString(),
    deployer: deployer.address,
    contracts: {
      GovernanceToken: await token.getAddress(),
      RoyaltyDistributor: await distributor.getAddress(),
      ExtractionTracker: await tracker.getAddress(),
      MiningOracle: await oracle.getAddress(),
      QuadraticVoting: await voting.getAddress(),
    },
    deployedAt: new Date().toISOString(),
  };

  fs.writeFileSync(
    "deployment-addresses.json",
    JSON.stringify(addresses, null, 2)
  );
  console.log("\nDeployment addresses saved to: deployment-addresses.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
