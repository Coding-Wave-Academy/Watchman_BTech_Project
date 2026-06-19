import os
import json
import time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Load .env manually
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip().strip('"').strip("'")

private_key = os.getenv("WATCHMAN_PRIVATE_KEY")
rpc_url = os.getenv("CELO_RPC_URL", "https://forno.celo-sepolia.celo-testnet.org")

if not private_key or private_key == "your_polygon_wallet_private_key":
    print("ERROR: Please set a valid WATCHMAN_PRIVATE_KEY in your .env file!")
    exit(1)

print(f"Connecting to {rpc_url}...")
w3 = Web3(Web3.HTTPProvider(rpc_url))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    print("ERROR: Failed to connect to RPC!")
    exit(1)

account = w3.eth.account.from_key(private_key)
print(f"Deploying from account: {account.address}")
print(f"Account Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} CELO")

if w3.eth.get_balance(account.address) == 0:
    print("ERROR: Account has 0 balance! You need Celo Sepolia CELO to deploy.")
    exit(1)

abi_path = os.path.join(BASE_DIR, "blockchain", "build", "contracts", "WatchmanAnchor.json")
if not os.path.exists(abi_path):
    print("ERROR: Contract ABI not found. Please run 'npx truffle compile' in the blockchain directory.")
    exit(1)

with open(abi_path) as f:
    contract_data = json.load(f)
    abi = contract_data["abi"]
    bytecode = contract_data["bytecode"]

Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
print("Building deployment transaction...")
tx = Contract.constructor().build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 2500000,
    'gasPrice': w3.eth.gas_price
})

print("Signing transaction...")
signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)

print("Broadcasting transaction...")
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Transaction Hash: {tx_hash.hex()}")
print("Waiting for confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = receipt.contractAddress
print(f"\n✅ Contract deployed successfully at address: {contract_address}")

# Update watchman.config.json
config_path = os.path.join(BASE_DIR, "data", "watchman.config.json")
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    config["blockchain"]["contract_address"] = contract_address
    config["blockchain"]["contract_abi_path"] = "blockchain/build/contracts/WatchmanAnchor.json"
    config["blockchain"]["demo_mode"] = False
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print("\n✅ Updated data/watchman.config.json with the new contract address and disabled demo_mode!")
else:
    print("\n⚠️ Could not find data/watchman.config.json to update automatically. Please update it manually.")

print("\nYou can now start the WatchMan backend! Your alerts will be anchored live to Celo Sepolia.")
