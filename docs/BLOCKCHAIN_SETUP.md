# Blockchain Setup

WatchMan NIDS leverages blockchain technology to ensure the immutability and integrity of generated security alerts. By default, the system runs in a "demo mode", but it can be configured to interact with a local Ganache network or the public Polygon network.

## How It Works
To avoid high transaction fees, WatchMan uses a **Merkle Tree batching mechanism**. Multiple alert hashes are combined into a Merkle Tree. Only the single Root Hash is sent (anchored) to the smart contract. The backend stores the Merkle proofs, allowing individual alerts to be verified mathematically against the on-chain root hash without storing every alert on the blockchain.

## Smart Contract Details
- **Contract Path**: `blockchain/contracts/NIDSLogger.sol`
- **Compiled ABI**: `blockchain/build/contracts/NIDSLogger.json`
- **Truffle Config**: `blockchain/truffle-config.js`

## 1. Local Testing with Ganache

Ganache provides a personal Ethereum blockchain for local development.

### Setup Steps:
1. **Install Ganache**: Download and install [Ganache](https://trufflesuite.com/ganache/) or use the CLI (`npm install -g ganache-cli`).
2. **Start Ganache**: Run Ganache on the default port `7545` (or update `truffle-config.js` if using a different port).
3. **Compile Contracts**:
   Navigate to the `blockchain/` directory and compile the Solidity contract:
   ```bash
   cd blockchain
   truffle compile
   ```
4. **Deploy Contracts**:
   Migrate the contract to your local Ganache network:
   ```bash
   truffle migrate --network development
   ```
5. **Update Configuration**:
   Copy the deployed contract address and update your NIDS configuration file (`data/watchman.config.json`):
   ```json
   {
     "blockchain": {
       "mode": "ganache",
       "rpc_url": "http://127.0.0.1:7545",
       "contract_address": "<YOUR_DEPLOYED_CONTRACT_ADDRESS>"
     }
   }
   ```

## 2. Deploying to Polygon (Testnet/Mainnet)

For a production-like environment, you can anchor hashes to the Polygon network.

### Setup Steps:
1. **Get a Provider URL**: Sign up for an RPC provider like Infura, Alchemy, or use a public Polygon RPC.
2. **Fund Your Wallet**: Ensure your deployment wallet has enough MATIC to cover gas fees. If using the Amoy Testnet, use a faucet.
3. **Configure Truffle**: Edit `blockchain/truffle-config.js` to include the Polygon network configuration, providing your wallet's mnemonic or private key (via environment variables).
4. **Deploy**:
   ```bash
   cd blockchain
   truffle migrate --network polygon
   ```
5. **Update Configuration**:
   Update `data/watchman.config.json` with the production details:
   ```json
   {
     "blockchain": {
       "mode": "polygon",
       "rpc_url": "<POLYGON_RPC_URL>",
       "contract_address": "<DEPLOYED_CONTRACT_ADDRESS>"
     }
   }
   ```

## 3. Manual Anchoring
You can manually trigger an anchoring cycle using the CLI:
```bash
python src/cli.py anchor
```
This forces the backend to compute the Merkle root of all unanchored alerts and send the transaction to the configured blockchain network.
