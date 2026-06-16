# WatchMan REST API Reference

The WatchMan NIDS provides a FastAPI backend. By default, it runs on `http://127.0.0.1:8000`.

## Interactive Docs

If you have enabled `debug` in `watchman_config.json`, you can view the interactive Swagger documentation at:
`http://127.0.0.1:8000/docs`

## Authentication

Most endpoints require a JSON Web Token (JWT).
You must pass this token in the `Authorization` header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. `POST /auth/login`
Authenticates a user and returns a JWT.
**Body:**
```json
{
  "username": "admin",
  "password": "yourpassword"
}
```
**Response:** `{"token": "eyJhb...", "user": {"username": "admin", "role": "admin"}}`

### 2. `GET /system/status`
Returns the daemon status, alert counts, and blockchain configuration.
**Requires:** Bearer Token.

### 3. `GET /alerts`
Retrieves a paginated list of alerts.
**Query Params:** `limit` (default 50), `attack_type`, `hours`
**Requires:** Bearer Token.

### 4. `PUT /alerts/{alert_id}/status`
Updates an alert status (e.g., to "blocked" or "active"). If set to "blocked", the IPS will ban the source IP.
**Body:** `{"status": "blocked"}`
**Requires:** Bearer Token (Admin Role).

### 5. `GET /verify/{alert_id}`
Cryptographically verifies an alert against the Blockchain Merkle Tree to ensure it hasn't been tampered with.
**Requires:** Bearer Token.

### 6. `WS /ws/alerts?token=<jwt>`
A WebSocket endpoint for streaming real-time alerts to the dashboard as soon as the ML engine detects them.
