import os
import datetime as dt

import bcrypt
import jwt
import psycopg2
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Resilience-Alpha Auth Service", version="1.0.0")

# Prometheus metrics: /metrics exposes http_requests_total (status codes let the
# ML engine see a spike of 401s during a brute-force attack).
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# --- Configuration (from environment) ---
DB_HOST = os.getenv("DB_HOST", "resilience_db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "resilience_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "super_secure_password_change_me")
DB_NAME = os.getenv("DB_NAME", "payment_si")

# JWT secret is read from the environment, never hard-coded. After a brute-force
# attack, the remediation engine can rotate it and restart this service.
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_random_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "15"))


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)


def client_ip(request: Request) -> str:
    # Behind the WAF the real client IP is forwarded in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/health")
def health_check():
    conn = get_db_connection()
    conn.close()
    return {"status": "healthy", "database": "connected"}


@app.post("/login")
def login(body: LoginRequest, request: Request):
    """Verifies credentials (bcrypt) and returns a short-lived JWT.
    Every failed attempt is logged with the source IP -> brute-force signal."""
    ip = client_ip(request)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (body.username,))
        row = cur.fetchone()
        ok = bool(row) and bcrypt.checkpw(body.password.encode(), row[1].encode())
        if not ok:
            # IMPORTANT: this log line and the 401 status are the brute-force signal.
            print(f'{{"event":"LOGIN_FAILED","username":"{body.username}","source_ip":"{ip}"}}')
            _audit(cur, conn, "LOGIN_FAILED", ip, {"username": body.username})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        now = dt.datetime.now(dt.timezone.utc)
        token = jwt.encode(
            {"sub": str(row[0]), "iat": now, "exp": now + dt.timedelta(minutes=JWT_TTL_MINUTES)},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        return {"access_token": token, "token_type": "bearer", "expires_in": JWT_TTL_MINUTES * 60}
    finally:
        cur.close()
        conn.close()


def _audit(cur, conn, event_type, ip, details):
    import json
    try:
        cur.execute(
            "INSERT INTO audit_logs (event_type, source_ip, details) VALUES (%s, %s, %s)",
            (event_type, ip, json.dumps(details)),
        )
        conn.commit()
    except Exception as e:
        print(f"audit_log_error: {e}")
