#! WTB integrated version 7th August 2025 Cyrus Clarke

from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

# Environment
INFURA_URL = os.getenv("INFURA_URL")
PK_A = os.getenv("PRIVATE_KEY_A")
PK_B = os.getenv("PRIVATE_KEY_B")

def _require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

_require(INFURA_URL, "Missing INFURA_URL in .env")
_require(PK_A, "Missing PRIVATE_KEY_A in .env")
_require(PK_B, "Missing PRIVATE_KEY_B in .env")

# Connect to Sepolia via Infura
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
_require(w3.is_connected(), "Web3 not connected — check INFURA_URL")

#manage transfers between players
ACCT_A = w3.eth.account.from_key(PK_A)
ACCT_B = w3.eth.account.from_key(PK_B)
ADDR_A = Web3.to_checksum_address(ACCT_A.address)
ADDR_B = Web3.to_checksum_address(ACCT_B.address)

# Optional: set nonzero values per resource (in ETH). Keep 0 while testing.
RESOURCE_VALUE_ETH = {
    "FIRE":  "0.0001",   # e.g. "0.001"
    "WATER": "0.0002",
    "LAND":  "0.0003",
    "ELECTRICITY": "0.0004",
}

def _acct_for_player(player: str):
    if player == "A":
        return ACCT_A, ADDR_B  # recipient is the *other* player (B)
    if player == "B":
        return ACCT_B, ADDR_A  # recipient is A
    raise ValueError(f"Unknown player '{player}' (expected 'A' or 'B')")


def trigger_transaction(player: str, resource: str) -> str:
    """
    Sends a direct P2P tx from the acting player's wallet to the *other* player's address.
    Encodes a short message in the data field. Returns tx hash hex string.
    """
    acct, recipient = _acct_for_player(player)
    nonce = w3.eth.get_transaction_count(acct.address)

    # Fees (EIP-1559). Fine for Sepolia.
    base = w3.eth.gas_price
    max_priority = Web3.to_wei('2', 'gwei')
    max_fee = base + Web3.to_wei('20', 'gwei')

    # Choose value by resource (still 0 by default)
    value_eth = RESOURCE_VALUE_ETH.get(resource.upper(), "0")
    value_wei = Web3.to_wei(value_eth, 'ether')

    # Encode message in data
    message = f"Player {player} traded {resource}"
    data_hex = Web3.to_hex(text=message)

    # First build a tx for gas estimation
    tx_for_gas = {
        "from": acct.address,
        "to": recipient,
        "value": value_wei,
        "data": data_hex,
    }
    gas_limit = w3.eth.estimate_gas(tx_for_gas)  # accounts for non-empty data


    tx = {
        "chainId": 11155111,  # Sepolia
        "nonce": nonce,
        "to": recipient,
        "value": value_wei,
        "gas": gas_limit,  # simple transfer; raise if you later call a contract
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority,
        "data": data_hex,
    }

    signed = acct.sign_transaction(tx)

    # Compatibility across Web3.py versions
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    if raw is None:
        raise RuntimeError("SignedTransaction missing raw transaction bytes")

    tx_hash = w3.eth.send_raw_transaction(raw)
    return w3.to_hex(tx_hash)