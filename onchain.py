#! WTB integrated version 20th August 2025 Cyrus Clarke 4p mode

from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

# Environment
INFURA_URL = os.getenv("INFURA_URL")

# Four player keys (0x-prefixed)
PK = {
    "Player1": os.getenv("PRIVATE_KEY_1"),
    "Player2": os.getenv("PRIVATE_KEY_2"),
    "Player3": os.getenv("PRIVATE_KEY_3"),
    "Player4": os.getenv("PRIVATE_KEY_4"),
}

def _require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

_require(INFURA_URL, "Missing INFURA_URL in .env")
for p in ["Player1", "Player2", "Player3", "Player4"]:
    _require(PK.get(p), f"Missing PRIVATE_KEY_{p[-1]} in .env (e.g. PRIVATE_KEY_1)")

# Connect to Sepolia via Infura
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
_require(w3.is_connected(), "Web3 not connected — check INFURA_URL")

# Build account/address maps
ACCT = {p: w3.eth.account.from_key(PK[p]) for p in PK}
ADDR = {p: Web3.to_checksum_address(ACCT[p].address) for p in PK}


# nonzero values per resource (in ETH).  0 while testing.
RESOURCE_VALUE_ETH = {
    "FIRE":  "0.0001",   
    "WATER": "0.0001",
    "LAND":  "0.0001",
    "ELECTRICITY": "0.0001",
}


def trigger_transaction(sender_player: str, opponent_player: str, resource: str) -> str:
    """
    Send a P2P EIP‑1559 transaction from `sender_player` to `opponent_player`.
    Encodes a short message about the trade in the data field.
    Returns the tx hash hex string.
    """
    if sender_player not in ACCT or opponent_player not in ADDR:
        raise ValueError(f"Unknown player(s): {sender_player}, {opponent_player}")

    acct = ACCT[sender_player]
    recipient = ADDR[opponent_player]

    # Fees
    base = w3.eth.gas_price
    max_priority = Web3.to_wei('2', 'gwei')
    max_fee = base + Web3.to_wei('20', 'gwei')

    # Value by resource
    value_eth = RESOURCE_VALUE_ETH.get(resource.upper(), "0")
    value_wei = Web3.to_wei(value_eth, "ether")

    # Payload text → bytes
    message = f"{sender_player}→{opponent_player} traded {resource}"
    data_hex = Web3.to_hex(text=message)

    # Nonce + gas estimate
    nonce = w3.eth.get_transaction_count(acct.address)
    tx_for_gas = {"from": acct.address, "to": recipient, "value": value_wei, "data": data_hex}
    gas_limit = w3.eth.estimate_gas(tx_for_gas)

    tx = {
        "chainId": 11155111,  # Sepolia
        "nonce": nonce,
        "to": recipient,
        "value": value_wei,
        "gas": gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority,
        "data": data_hex,
    }

    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    if raw is None:
        raise RuntimeError("SignedTransaction missing raw tx bytes")

    tx_hash = w3.eth.send_raw_transaction(raw)
    return w3.to_hex(tx_hash)

# Optional helper to print addresses once:
if __name__ == "__main__":
    for p in ["Player1","Player2","Player3","Player4"]:
        print(f"{p}: {ADDR[p]}")