# Changelog

## [1.0.0] - Pre-Release Stabilization

### Added
- **Modern Landing Page**: Created `index.html` with a professional, aesthetic showcase of WatchMan's NIDS and Blockchain capabilities.
- **Documentation Suite**: Added `SECURITY.md`, `FAQ.md`, and `TROUBLESHOOTING.md`.
- **Dynamic Topology**: Implemented `GET /system/topology` to generate real-time network graphs based on packet capture data.
- **Blockchain Ledger View**: Implemented `GET /system/ledger` to fetch real anchored alerts with Merkle roots.
- **Historical Trends**: Implemented `GET /alerts/trends` for 24-hour attack trend visualization.

### Changed
- **Dashboard Theme**: Converted the entire React dashboard from a dark mode to a premium Light Mode theme (`index.css` overhaul).
- **Typography**: Migrated all fonts to standard `Inter` Google Font for modern legibility.
- **Backend Integrations**: Stripped all mock and fallback data from `Dashboard.tsx`, `Alerts.tsx`, `Topology.tsx`, and `Ledger.tsx`. Components now fetch live data natively.

### Fixed
- **Repository Bloat**: Purged `.venv/` and `node_modules/` from Git history, drastically reducing the repository footprint for push synchronization to GitHub.
