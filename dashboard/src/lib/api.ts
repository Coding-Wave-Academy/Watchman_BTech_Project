const API_BASE = window.location.origin;

interface LoginPayload {
  username: string;
  password: string;
}

interface LoginResponse {
  token: string;
  user: { username: string; role: string };
}

let authToken: string | null = localStorage.getItem("watchman_token");

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Auto-login since the UI has no login page yet
  if (!authToken && !path.startsWith("/auth/login")) {
    try {
      const loginRes = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "admin", password: "watchman2026" })
      });
      if (loginRes.ok) {
        const data = await loginRes.json();
        authToken = data.token;
        localStorage.setItem("watchman_token", data.token);
      }
    } catch {
      // Ignore login errors, it will just fail the next request
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: getHeaders(),
    ...options,
  });
  if (res.status === 401) {
    authToken = null;
    localStorage.removeItem("watchman_token");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API Error ${res.status}`);
  }
  return res.json();
}

// ─── Auth ───────────────────────────────────────────
export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  authToken = data.token;
  localStorage.setItem("watchman_token", data.token);
  return data;
}

export function logout() {
  authToken = null;
  localStorage.removeItem("watchman_token");
}

export function isAuthenticated(): boolean {
  return !!authToken;
}

// ─── Alerts ─────────────────────────────────────────
export interface Alert {
  alert_id: string;
  timestamp: string;
  src_ip: string;
  dst_ip: string;
  attack_type: string;
  confidence: number;
  status: string;
  merkle_root?: string;
  tx_hash?: string;
}

export async function fetchAlerts(limit = 50, attackType?: string, hours?: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (attackType) params.set("attack_type", attackType);
  if (hours) params.set("hours", String(hours));
  return apiFetch<{ alerts: Alert[] }>(`/alerts?${params}`);
}

export async function fetchAlertStats() {
  return apiFetch<Record<string, unknown>>("/alerts/stats");
}

export async function updateAlertStatus(alertId: string, status: string) {
  return apiFetch<Alert>(`/alerts/${alertId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

// ─── System ─────────────────────────────────────────
export async function fetchSystemStatus() {
  return apiFetch<Record<string, unknown>>("/system/status");
}

export async function startCapture() {
  return apiFetch<Record<string, unknown>>("/system/start", { method: "POST" });
}

export async function stopCapture() {
  return apiFetch<Record<string, unknown>>("/system/stop", { method: "POST" });
}

export async function triggerAnchor() {
  return apiFetch<Record<string, unknown>>("/system/anchor", { method: "POST" });
}

// ─── Verification ───────────────────────────────────
export async function verifyAlert(alertId: string) {
  return apiFetch<Record<string, unknown>>(`/verify/${alertId}`);
}

export async function fetchSystemLedger(limit: number = 50, offset: number = 0) {
  return apiFetch<{ blocks: any[]; total: number }>(`/system/ledger?limit=${limit}&offset=${offset}`);
}

export async function fetchSystemTopology() {
  return apiFetch<{ nodes: any[]; edges: any[] }>("/system/topology");
}

export async function fetchAlertTrends() {
  return apiFetch<any[]>("/alerts/trends");
}

// ─── Health ─────────────────────────────────────────
export async function fetchHealth() {
  return apiFetch<{ status: string; service: string }>("/health");
}

// ─── WebSocket ──────────────────────────────────────
export function connectAlertStream(onAlert: (alert: Alert) => void): WebSocket | null {
  if (!authToken) return null;
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/alerts?token=${authToken}`);
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "alert" && msg.alert) {
        onAlert(msg.alert);
      }
    } catch {
      // ignore parse errors
    }
  };
  return ws;
}
