"""
Oracle Bridge — Translates AI agent outputs into blockchain oracle submissions.

This is the bridge between the Python AI world and the Polygon blockchain.
When the super-agent analyzes mineral data, the oracle bridge submits the
results on-chain where they become immutable, transparent, and verifiable.

Data flow:
    Community member → Telegram/Flutter → Super-Agent (AI analysis) →
    Oracle Bridge → MiningOracle.sol → ExtractionTracker.sol

No human touches the data after submission. The bridge is the translator
between intelligence and truth.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class OracleConfig:
    """Configuration for the oracle bridge."""
    rpc_url: str                    # Polygon RPC endpoint (Alchemy/Infura/QuickNode)
    oracle_private_key: str         # Oracle wallet private key
    oracle_address: str             # MiningOracle.sol contract address
    extraction_tracker_address: str # ExtractionTracker.sol contract address
    chain_id: int = 137             # Polygon mainnet (80001 for Mumbai testnet)
    gas_limit: int = 300000
    max_fee_multiplier: float = 2.0


class OracleBridge:
    """
    Bridge between the AI super-agent and the blockchain.

    Translates tool registry outputs (geological analysis, satellite data,
    market prices, vision analysis) into on-chain oracle submissions.
    """

    def __init__(self, config: Optional[OracleConfig] = None):
        self.config = config or self._load_config()
        self._w3 = None
        self._account = None
        self._oracle_contract = None
        self._tracker_contract = None

    def _load_config(self) -> OracleConfig:
        """Load config from environment variables."""
        return OracleConfig(
            rpc_url=os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com"),
            oracle_private_key=os.environ.get("ORACLE_PRIVATE_KEY", ""),
            oracle_address=os.environ.get("MINING_ORACLE_ADDRESS", ""),
            extraction_tracker_address=os.environ.get("EXTRACTION_TRACKER_ADDRESS", ""),
            chain_id=int(os.environ.get("CHAIN_ID", "137")),
        )

    def _ensure_web3(self):
        """Lazy-initialize Web3 connection."""
        if self._w3 is None:
            try:
                from web3 import Web3
                from eth_account import Account

                self._w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
                self._account = Account.from_key(self.config.oracle_private_key)

                # Load contract ABIs (generated from Hardhat compilation)
                self._oracle_contract = self._w3.eth.contract(
                    address=self.config.oracle_address,
                    abi=self._load_abi("MiningOracle")
                )
                self._tracker_contract = self._w3.eth.contract(
                    address=self.config.extraction_tracker_address,
                    abi=self._load_abi("ExtractionTracker")
                )

                logger.info("Oracle bridge initialized: %s", self._account.address)
            except ImportError:
                logger.error("web3 not installed. Run: pip install web3 eth-account")
                raise
            except Exception as e:
                logger.error("Failed to initialize oracle bridge: %s", e)
                raise

    def _load_abi(self, contract_name: str) -> list:
        """Load contract ABI from compiled artifacts."""
        abi_path = f"contracts/artifacts/{contract_name}.json"
        try:
            with open(abi_path) as f:
                artifact = json.load(f)
                return artifact.get("abi", [])
        except FileNotFoundError:
            logger.warning("ABI not found for %s — using empty ABI", contract_name)
            return []

    def _hash_data(self, data: dict[str, Any]) -> bytes:
        """Create deterministic hash of data for on-chain integrity check."""
        canonical = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(canonical).digest()

    def _location_hash(self, lat: float, lon: float) -> bytes:
        """Create on-chain location hash from coordinates."""
        from web3 import Web3
        return Web3.solidity_keccak(
            ['uint256', 'uint256'],
            [int(lat * 1e6), int(lon * 1e6)]
        )

    async def submit_observation(
        self,
        observation: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Submit a verified mineral observation to the blockchain.

        Args:
            observation: Dict containing:
                - lat, lon: GPS coordinates
                - mineral_type: "gold", "copper", etc.
                - estimated_value_kes: Estimated value in KES
                - confidence: AI confidence score (0.0 - 1.0)
                - source: "vision", "satellite", "geological", etc.
                - raw_data: Full analysis data

        Returns:
            Dict with transaction hash and status
        """
        self._ensure_web3()

        if not self.config.oracle_private_key:
            return {
                "success": False,
                "error": "Oracle private key not configured",
                "action": "Set ORACLE_PRIVATE_KEY environment variable"
            }

        try:
            location_hash = self._location_hash(
                observation["lat"],
                observation["lon"]
            )
            data_hash = self._hash_data(observation.get("raw_data", observation))
            confidence_bps = int(observation.get("confidence", 0.5) * 10000)

            # Build transaction
            tx = self._oracle_contract.functions.submitData(
                location_hash,
                observation.get("mineral_type", "unknown"),
                int(observation.get("estimated_value_kes", 0)),
                confidence_bps,
                data_hash
            ).build_transaction({
                'from': self._account.address,
                'nonce': self._w3.eth.get_transaction_count(self._account.address),
                'gas': self.config.gas_limit,
                'maxFeePerGas': int(
                    self._w3.eth.gas_price * self.config.max_fee_multiplier
                ),
                'maxPriorityFeePerGas': self._w3.to_wei(30, 'gwei'),
                'chainId': self.config.chain_id,
            })

            # Sign and send
            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )

            logger.info(
                "Oracle submission confirmed: tx=%s block=%d",
                tx_hash.hex(),
                receipt.blockNumber
            )

            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "location_hash": location_hash.hex(),
                "mineral_type": observation.get("mineral_type"),
                "confidence_bps": confidence_bps,
            }

        except Exception as e:
            logger.exception("Oracle submission failed")
            return {
                "success": False,
                "error": str(e),
                "observation": observation,
            }

    async def record_extraction(
        self,
        extraction: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Record an extraction event on-chain (ExtractionTracker NFT).

        Args:
            extraction: Dict containing:
                - lat, lon: GPS coordinates
                - mineral_type: What was extracted
                - estimated_grade_bps: Grade in basis points
                - estimated_value_kes: Value in KES
                - confidence: AI confidence (0.0 - 1.0)
                - ipfs_uri: IPFS metadata URI
                - notes: Free-text notes

        Returns:
            Dict with transaction hash and NFT token ID
        """
        self._ensure_web3()

        if not self.config.oracle_private_key:
            return {"success": False, "error": "Oracle key not configured"}

        try:
            location_hash = self._location_hash(
                extraction["lat"],
                extraction["lon"]
            )
            confidence_bps = int(extraction.get("confidence", 0.5) * 10000)

            tx = self._tracker_contract.functions.recordExtraction(
                location_hash,
                extraction.get("mineral_type", "unknown"),
                int(extraction.get("estimated_grade_bps", 0)),
                int(extraction.get("estimated_value_kes", 0)),
                confidence_bps,
                extraction.get("ipfs_uri", ""),
                extraction.get("notes", "")
            ).build_transaction({
                'from': self._account.address,
                'nonce': self._w3.eth.get_transaction_count(self._account.address),
                'gas': self.config.gas_limit,
                'maxFeePerGas': int(
                    self._w3.eth.gas_price * self.config.max_fee_multiplier
                ),
                'maxPriorityFeePerGas': self._w3.to_wei(30, 'gwei'),
                'chainId': self.config.chain_id,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )

            logger.info("Extraction recorded: tx=%s", tx_hash.hex())

            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "location_hash": location_hash.hex(),
            }

        except Exception as e:
            logger.exception("Extraction recording failed")
            return {"success": False, "error": str(e)}

    async def check_connection(self) -> dict[str, Any]:
        """Check if the oracle bridge is connected to Polygon."""
        try:
            self._ensure_web3()
            connected = self._w3.is_connected()
            block = self._w3.eth.block_number if connected else None
            balance = None

            if connected and self._account:
                balance_wei = self._w3.eth.get_balance(self._account.address)
                balance = float(self._w3.from_wei(balance_wei, 'ether'))

            return {
                "connected": connected,
                "chain_id": self.config.chain_id,
                "latest_block": block,
                "oracle_address": self._account.address if self._account else None,
                "balance_matic": balance,
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
_bridge: Optional[OracleBridge] = None


def get_oracle_bridge() -> OracleBridge:
    """Get or create the singleton oracle bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = OracleBridge()
    return _bridge


async def submit_to_chain(observation: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to submit an observation to the blockchain."""
    bridge = get_oracle_bridge()
    return await bridge.submit_observation(observation)
