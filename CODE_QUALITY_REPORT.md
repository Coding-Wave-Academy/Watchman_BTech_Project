# CODE QUALITY REPORT

## 1. Overview
This report evaluates the code quality, maintainability, and structural soundness of the WatchMan NIDS repository (Phase 4 of the project audit). The assessment covers Python (Backend), JavaScript (Electron/Frontend), and Solidity (Smart Contracts).

---

## 2. General Assessment
Overall, the code is well-structured for a Bachelor's level final-year project. The separation of concerns between the Machine Learning pipeline, the FastAPI web layer, the Scapy packet sniffer, and the Electron frontend is logical and modular. However, it lacks several production-grade software engineering practices.

## 3. Specific Findings

### 3.1 Logging vs. Printing
*   **Issue:** Across the backend (`src/predict.py`, `src/app.py`, `src/ganache_manager.py`), the code relies heavily on standard `print()` statements for output.
*   **Impact:** Since WatchMan is intended to run as a background daemon (spawned by Electron), `print` statements are lost unless stdout is manually piped to a file. It makes debugging in production near impossible.
*   **Recommendation:** Implement the standard Python `logging` module. Configure rotating file handlers and define appropriate log levels (`INFO`, `DEBUG`, `ERROR`).

### 3.2 Error Handling
*   **Issue:** Widespread use of broad `except Exception as e:` blocks, particularly in the packet processing loop (`src/predict.py`) and blockchain communication (`src/blockchain.py`).
*   **Impact:** Catching all exceptions blindly can mask severe underlying bugs (e.g., `KeyError` or `TypeError`) and makes the system fail silently without providing actionable stack traces.
*   **Recommendation:** Catch specific exceptions (e.g., `scapy.error.Scapy_Exception`, `web3.exceptions.ContractLogicError`) and ensure that unexpected exceptions bubble up or are logged with a full stack trace.

### 3.3 Type Hinting and Docstrings
*   **Issue:** While some newer modules (like `src/auth.py` and `src/app.py`) use Python type hints (`from typing import ...`), the core ML and data processing scripts (`src/predict.py`, `src/merkle.py`) largely omit them.
*   **Impact:** Reduced IDE support and increased cognitive load for future maintainers trying to understand what shapes of data (e.g., what a `flow_key` or `flow_packets` dictionary looks like) are expected.
*   **Recommendation:** Adopt strict type hinting across all Python files (`mypy` compliance) and enforce standard docstrings (Google or Sphinx format) for all classes and methods.

### 3.4 Hardcoded Configuration
*   **Issue:** Several paths and constants are hardcoded within the source files rather than being pulled from `watchman.config.json` or `.env`. For example, `MODEL_PATH = 'models/'` in `predict.py`.
*   **Impact:** If the application is run from a different working directory, or if models need to be stored elsewhere, the application will crash (`FileNotFoundError`).
*   **Recommendation:** Centralize all configuration within `src/watchman_config.py`. Use absolute paths constructed via `pathlib.Path(__file__).parent` to resolve relative file locations dynamically.

### 3.5 Electron Frontend Code
*   **Issue:** The Electron setup lacks a proper bundler (like Webpack or Vite) for the frontend logic. The JS logic in `onboarding.html` and `dashboard/index.html` is embedded directly into the HTML `<script>` tags.
*   **Impact:** Harder to test UI components in isolation, reuse code, or manage third-party dependencies securely.
*   **Recommendation:** Refactor the UI to use a modern framework (React, Vue, or modular Vanilla JS) with a build step, separating HTML, CSS, and JS into discrete files.

---

## 4. Conclusion
The codebase is functional and effectively demonstrates the project's core concepts. To transition from an academic prototype to a maintainable open-source tool, the immediate priorities should be implementing standard `logging`, improving exception handling, and centralizing configuration.
