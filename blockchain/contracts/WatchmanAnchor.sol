// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * WatchmanAnchor.sol
 * NIDS + ML + Blockchain Project
 *
 * PURPOSE:
 *   Provides tamper-proof, immutable logging of NIDS alert batches using Merkle Roots.
 */

contract WatchmanAnchor {
    address public owner;
    uint256 public totalBatches;

    event RootAnchored(
        string batchId,
        uint256 count,
        string rootHash,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "WatchmanAnchor: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        totalBatches = 0;
    }

    function logRoot(string memory batchId, uint256 count, string memory rootHash) public onlyOwner {
        totalBatches++;
        emit RootAnchored(batchId, count, rootHash, block.timestamp);
    }
}
