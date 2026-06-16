# Electron Removal Report

## Audit Findings

A full audit of the WatchMan NIDS repository identified the following Electron-related components to be removed as part of the CLI-first architectural refactor:

### 1. Directories and Files to Remove
- `electron/` (entire directory containing `main.js`, `preload.js`, and `renderer/` if any)
- Any desktop packaging scripts or artifacts generated in `dist/` and `backend_dist/`.

### 2. Dependencies to Remove (`package.json`)
- `electron` (devDependencies)
- `electron-builder` (devDependencies)
- Build configurations such as `"build": { ... }` block targeting Windows (`nsis`), Mac (`dmg`), and Linux (`AppImage`).

### 3. Build Scripts to Remove (`package.json`)
- `"start": "electron ."`
- `"dev": "electron . --inspect"`
- `"build": "npm run build:backend && electron-builder --dir"`
- `"dist": "npm run build:backend && electron-builder"`

### 4. Code Paths Affected
The primary interaction model shifts from a local desktop application to a background daemon managed via systemd and CLI. The backend (`src/app.py`) will now serve as the standalone core, eliminating the need for `app.isPackaged` or `process.resourcesPath` checks on the frontend. The dashboard will be accessed strictly via standard web browsers.

---

**Status:** Verified. Proceeding with deletion and `package.json` cleanup.
