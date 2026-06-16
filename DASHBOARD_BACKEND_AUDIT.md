# Dashboard Backend Audit

**Phase 5: Connect Dashboard to Backend**

## 1. Current State of Mock Data

I audited the four main pages of the dashboard to identify hardcoded or fallback data:

*   **`Dashboard.tsx`:** 
    *   Currently tries to fetch from `/alerts`, `/alerts/stats`, and `/system/status`.
    *   However, if the API call fails, it falls back to a hardcoded array of alerts.
    *   The `24h Attack Trends` chart uses `FALLBACK_CHART_DATA`.

*   **`Alerts.tsx`:** 
    *   Tries to fetch from `/alerts`.
    *   Contains a hardcoded fallback array of 5 alerts.
    *   `totalActive` and `totalBlocked` rely on the fetched data, but the KPI numbers are hardcoded if undefined (e.g., `totalBlocked || "1,042"`).
    *   "Verified Logs" KPI is hardcoded to `8,921`.

*   **`Ledger.tsx`:**
    *   Completely hardcoded. Uses a randomly generated `MOCK_BLOCKS` array of 50 items.
    *   KPIs like `1,284,902` total blocks are hardcoded.

*   **`Topology.tsx`:**
    *   Completely hardcoded. Uses `MOCK_NODES` and `MOCK_EDGES`.

## 2. Required Backend Endpoints

To strictly fulfill the requirement "Do not create mock functionality. Do not hardcode data. All dashboard information must come from the backend," I must augment `src/app.py` and `src/db.py` to provide the missing data:

1.  **Topology Data:** The NIDS doesn't actively scan the network (it's passive). However, we can build a topology graph dynamically by querying the database for all unique `source_ip` and `target_ip` relationships seen in the traffic.
    *   *Action:* Create `GET /system/topology` in `app.py`.

2.  **Ledger Data:** The blockchain ledger should show actual anchored alerts.
    *   *Action:* Create `GET /system/ledger` in `app.py` to fetch alerts where `tx_hash IS NOT NULL`.

3.  **Chart Data:** 
    *   *Action:* Create `GET /alerts/trends` to group alerts by hour for the chart.

## 3. Integration Plan

1.  Update `src/db.py` to add `get_topology()`, `get_ledger()`, and `get_trends()`.
2.  Update `src/app.py` to expose these as REST endpoints.
3.  Update `dashboard/src/lib/api.ts` to include fetch functions for the new endpoints.
4.  Remove all `MOCK_*` arrays and fallback objects from the React components. They will now display loading states or empty states if no data exists.
