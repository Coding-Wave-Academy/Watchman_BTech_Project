// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * NIDSLogger.sol
 * NIDS + ML + Blockchain Project — BTech
 *
 * PURPOSE:
 *   Provides tamper-proof, immutable logging of network
 *   intrusion alerts detected by the ML engine.
 *
 * DESIGN:
 *   - Alerts are stored on-chain as structs
 *   - Once written, no alert can be modified or deleted
 *   - Any tampering attempt is detectable via hash verification
 *   - Only the contract owner (NIDS system) can log alerts
 *   - Anyone can read and verify logs (transparency)
 */

contract NIDSLogger {

    // ─────────────────────────────────────────────
    // DATA STRUCTURES
    // ─────────────────────────────────────────────

    struct Alert {
        uint256 id;           // sequential alert ID
        uint256 timestamp;    // block timestamp (Unix)
        string  srcIP;        // source IP address
        string  dstIP;        // destination IP address
        uint16  srcPort;      // source port
        uint16  dstPort;      // destination port
        string  alertType;    // DoS / PortScan / BruteForce / Anomaly
        string  severity;     // CRITICAL / HIGH / MEDIUM / INFO
        uint8   confidence;   // RF confidence 0-100
        bytes32 alertHash;    // keccak256 hash of alert data
    }

    // ─────────────────────────────────────────────
    // STATE VARIABLES
    // ─────────────────────────────────────────────

    address public owner;
    uint256 public alertCount;

    // Main storage: alert ID → Alert struct
    mapping(uint256 => Alert) private alerts;

    // IP-based index: track alerts per source IP
    mapping(string => uint256[]) private alertsByIP;

    // Type-based index: track alerts per attack type
    mapping(string => uint256[]) private alertsByType;

    // ─────────────────────────────────────────────
    // EVENTS
    // ─────────────────────────────────────────────

    event AlertLogged(
        uint256 indexed id,
        uint256 timestamp,
        string  srcIP,
        string  alertType,
        string  severity,
        bytes32 alertHash
    );

    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    // ─────────────────────────────────────────────
    // MODIFIERS
    // ─────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "NIDSLogger: caller is not the owner");
        _;
    }

    // ─────────────────────────────────────────────
    // CONSTRUCTOR
    // ─────────────────────────────────────────────

    constructor() {
        owner      = msg.sender;
        alertCount = 0;
    }

    // ─────────────────────────────────────────────
    // WRITE FUNCTIONS
    // ─────────────────────────────────────────────

    /**
     * @dev Log a new intrusion alert on-chain.
     * Only callable by contract owner (NIDS system).
     * Returns the alert ID assigned to this entry.
     */
    function logAlert(
        string  memory _srcIP,
        string  memory _dstIP,
        uint16         _srcPort,
        uint16         _dstPort,
        string  memory _alertType,
        string  memory _severity,
        uint8          _confidence
    ) public onlyOwner returns (uint256) {

        alertCount++;

        // Compute tamper-proof hash of all alert fields
        bytes32 alertHash = keccak256(abi.encodePacked(
            alertCount,
            block.timestamp,
            _srcIP,
            _dstIP,
            _srcPort,
            _dstPort,
            _alertType,
            _severity,
            _confidence
        ));

        // Store alert
        alerts[alertCount] = Alert({
            id          : alertCount,
            timestamp   : block.timestamp,
            srcIP       : _srcIP,
            dstIP       : _dstIP,
            srcPort     : _srcPort,
            dstPort     : _dstPort,
            alertType   : _alertType,
            severity    : _severity,
            confidence  : _confidence,
            alertHash   : alertHash
        });

        // Update indexes
        alertsByIP[_srcIP].push(alertCount);
        alertsByType[_alertType].push(alertCount);

        emit AlertLogged(
            alertCount,
            block.timestamp,
            _srcIP,
            _alertType,
            _severity,
            alertHash
        );

        return alertCount;
    }

    // ─────────────────────────────────────────────
    // READ FUNCTIONS
    // ─────────────────────────────────────────────

    /**
     * @dev Retrieve a single alert by ID.
     */
    function getAlert(uint256 _id) public view returns (Alert memory) {
        require(_id > 0 && _id <= alertCount, "NIDSLogger: alert ID out of range");
        return alerts[_id];
    }

    /**
     * @dev Get all alert IDs for a given source IP.
     */
    function getAlertsByIP(string memory _srcIP)
        public view returns (uint256[] memory)
    {
        return alertsByIP[_srcIP];
    }

    /**
     * @dev Get all alert IDs for a given attack type.
     */
    function getAlertsByType(string memory _alertType)
        public view returns (uint256[] memory)
    {
        return alertsByType[_alertType];
    }

    /**
     * @dev Get the most recent N alerts.
     * Useful for dashboard display.
     */
    function getRecentAlerts(uint256 _count)
        public view returns (Alert[] memory)
    {
        uint256 count  = _count > alertCount ? alertCount : _count;
        Alert[] memory result = new Alert[](count);

        for (uint256 i = 0; i < count; i++) {
            result[i] = alerts[alertCount - i];
        }

        return result;
    }

    /**
     * @dev Verify integrity of a stored alert.
     * Recomputes hash and compares to stored value.
     * Returns true if untampered, false if corrupted.
     */
    function verifyAlert(uint256 _id) public view returns (bool) {
        require(_id > 0 && _id <= alertCount, "NIDSLogger: alert ID out of range");

        Alert memory a = alerts[_id];

        bytes32 recomputedHash = keccak256(abi.encodePacked(
            a.id,
            a.timestamp,
            a.srcIP,
            a.dstIP,
            a.srcPort,
            a.dstPort,
            a.alertType,
            a.severity,
            a.confidence
        ));

        return recomputedHash == a.alertHash;
    }

    /**
     * @dev Get total alert count.
     */
    function getTotalAlerts() public view returns (uint256) {
        return alertCount;
    }

    // ─────────────────────────────────────────────
    // ADMIN FUNCTIONS
    // ─────────────────────────────────────────────

    /**
     * @dev Transfer contract ownership to a new address.
     * Used when NIDS system account changes.
     */
    function transferOwnership(address _newOwner) public onlyOwner {
        require(_newOwner != address(0), "NIDSLogger: new owner is zero address");
        emit OwnershipTransferred(owner, _newOwner);
        owner = _newOwner;
    }
}
