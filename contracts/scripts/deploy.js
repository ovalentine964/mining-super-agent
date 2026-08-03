/**
 * Sovereign Resource DAO — Deployment Script
 *
 * Deploys all smart contracts to Polygon (Amoy testnet or mainnet).
 *
 * ⚠️  PREREQUISITE: Deploy a multisig wallet (e.g., Safe) FIRST.
 *     The deployer address will receive initial admin roles.
 *     After deployment, transfer admin roles to the multisig.
 *     NEVER use an EOA as the long-term admin.
 *
 * ⚠️  PLACEHOLDER ADDRESSES: The following must be replaced with real addresses
 *     before mainnet deployment:
 *       - devFund (line ~40)
 *       - communityWallet (line ~41)
 *       - reserve (line ~42)
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network amoy      (testnet)
 *   npx hardhat run scripts/deploy.js --network polygon    (mainnet)
 */

const { ethers, upgrades, run } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  // ── 0. Multisig check ──────────────────────────────────────────
  // ⚠️  Deploy a multisig wallet (Gnosis Safe / Safe{Wallet}) BEFORE running this script.
  //     All admin roles should be transferred to the multisig after deployment.
  //     The deployer EOA is used here only for initial setup.
  console.log("\n⚠️  Ensure multisig is deployed before mainnet deployment!");

  // ── 1. Deploy Governance Token ($MINE) ──────────────────────────
  console.log("\n1. Deploying GovernanceToken ($MINE)...");
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
  const token = await GovernanceToken.deploy();
  await token.waitForDeployment();
  const tokenAddr = await token.getAddress();
  console.log("   GovernanceToken deployed to:", tokenAddr);

  // ── 2. Deploy RoyaltyDistributor (UUPS Proxy) ───────────────────
  console.log("\n2. Deploying RoyaltyDistributor (proxy)...");
  const RoyaltyDistributor = await ethers.getContractFactory("RoyaltyDistributor");

  // ⚠️  PLACEHOLDER ADDRESSES — replace with real addresses before mainnet
  const devFund = deployer.address;          // TODO: Replace with actual dev fund multisig
  const communityWallet = deployer.address;  // TODO: Replace with actual community wallet
  const reserve = deployer.address;          // TODO: Replace with actual reserve address

  const distributor = await upgrades.deployProxy(
    RoyaltyDistributor,
    [devFund, communityWallet, reserve, deployer.address],
    { initializer: "initialize" }
  );
  await distributor.waitForDeployment();
  const distributorAddr = await distributor.getAddress();
  console.log("   RoyaltyDistributor deployed to:", distributorAddr);

  // ── 3. Deploy ExtractionTracker ─────────────────────────────────
  console.log("\n3. Deploying ExtractionTracker...");
  const ExtractionTracker = await ethers.getContractFactory("ExtractionTracker");
  const tracker = await ExtractionTracker.deploy();
  await tracker.waitForDeployment();
  const trackerAddr = await tracker.getAddress();
  console.log("   ExtractionTracker deployed to:", trackerAddr);

  // ── 4. Deploy MiningOracle ──────────────────────────────────────
  console.log("\n4. Deploying MiningOracle...");
  const MiningOracle = await ethers.getContractFactory("MiningOracle");
  const oracle = await MiningOracle.deploy();
  await oracle.waitForDeployment();
  const oracleAddr = await oracle.getAddress();
  console.log("   MiningOracle deployed to:", oracleAddr);

  // ── 5. Deploy QuadraticVoting ───────────────────────────────────
  console.log("\n5. Deploying QuadraticVoting...");
  const QuadraticVoting = await ethers.getContractFactory("QuadraticVoting");
  const voting = await QuadraticVoting.deploy(tokenAddr);
  await voting.waitForDeployment();
  const votingAddr = await voting.getAddress();
  console.log("   QuadraticVoting deployed to:", votingAddr);

  // ── 6. Grant roles ─────────────────────────────────────────────
  console.log("\n6. Granting roles...");

  // ExtractionTracker: grant ORACLE_ROLE to MiningOracle contract
  const ORACLE_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ORACLE_ROLE"));
  const VERIFIER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("VERIFIER_ROLE"));
  const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));

  console.log("   Granting ORACLE_ROLE on ExtractionTracker to MiningOracle...");
  await (await tracker.grantRole(ORACLE_ROLE, oracleAddr)).wait();

  console.log("   Granting ORACLE_ROLE on MiningOracle to oracle bridge (deployer placeholder)...");
  // TODO: Replace deployer.address with the actual oracle bridge address
  await (await oracle.grantRole(ORACLE_ROLE, deployer.address)).wait();

  console.log("   Granting MINTER_ROLE on GovernanceToken to deployer (placeholder)...");
  // TODO: Replace deployer.address with the actual minting authority (multisig or vesting contract)
  await (await token.grantRole(MINTER_ROLE, deployer.address)).wait();

  console.log("   ✅ Roles granted. Review and transfer admin to multisig post-deployment.");

  // ── 7. Summary ─────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("SOVEREIGN RESOURCE DAO — DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log({
    GovernanceToken: tokenAddr,
    RoyaltyDistributor: distributorAddr,
    ExtractionTracker: trackerAddr,
    MiningOracle: oracleAddr,
    QuadraticVoting: votingAddr,
  });
  console.log("=".repeat(60));

  // Save deployment addresses
  const fs = require("fs");
  const network = await deployer.provider.getNetwork();
  const addresses = {
    network: network.name,
    chainId: network.chainId.toString(),
    deployer: deployer.address,
    contracts: {
      GovernanceToken: tokenAddr,
      RoyaltyDistributor: distributorAddr,
      ExtractionTracker: trackerAddr,
      MiningOracle: oracleAddr,
      QuadraticVoting: votingAddr,
    },
    deployedAt: new Date().toISOString(),
  };

  fs.writeFileSync(
    "deployment-addresses.json",
    JSON.stringify(addresses, null, 2)
  );
  console.log("\nDeployment addresses saved to: deployment-addresses.json");

  // ── 8. Verify contracts on block explorer ───────────────────────
  // Run separately: npx hardhat verify --network amoy <CONTRACT_ADDRESS>
  console.log("\n📋 Contract verification commands (run after deployment):");
  console.log(`   npx hardhat verify --network amoy ${tokenAddr}`);
  console.log(`   npx hardhat verify --network amoy ${trackerAddr}`);
  console.log(`   npx hardhat verify --network amoy ${oracleAddr}`);
  console.log(`   npx hardhat verify --network amoy ${votingAddr} "${tokenAddr}"`);
  console.log("   (RoyaltyDistributor is a proxy — verify implementation only via upgrades plugin)");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
