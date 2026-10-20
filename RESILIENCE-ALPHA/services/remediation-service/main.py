import os
import time

import docker
import requests
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Resilience-Alpha Remediation Engine", version="1.0.0")

# Initialize Docker client using the mounted socket
try:
    client = docker.from_env()
except Exception as e:
    print(f"Failed to connect to Docker socket: {e}")
    client = None

PAYMENT_URL = os.getenv("PAYMENT_URL", "http://resilience_payment:8002")
PAYMENT_CONTAINER = os.getenv("PAYMENT_CONTAINER", "resilience_payment")
AUTH_CONTAINER = os.getenv("AUTH_CONTAINER", "resilience_auth")
BLOCKLIST_PATH = os.getenv("WAF_BLOCKLIST_PATH", "/shared/blocklist.conf")
WAF_RELOAD_URL = os.getenv("WAF_RELOAD_URL", "http://resilience_waf:8080/_admin/reload")

# In-memory history of incidents, exposed for the dashboard.
INCIDENTS: list[dict] = []

# Decision table: incident type -> ordered list of actions.
PLAYBOOKS = {
    "bruteforce": ["block_ip", "restart_auth"],
    "injection": ["block_ip", "check_integrity"],
    "flood": ["block_ip", "restart_payment"],
    "service_down": ["restart_payment"],
    "anomaly": ["restart_payment"],
}


class RemediationRequest(BaseModel):
    reason: str = "ML_ANOMALY_DETECTED"
    type: str = "anomaly"
    source_ip: str = "unknown"


@app.get("/health")
def health_check():
    return {"status": "healthy", "docker_connected": client is not None}


@app.get("/incidents/latest")
def latest_incident():
    return INCIDENTS[-1] if INCIDENTS else {}


@app.get("/incidents")
def all_incidents():
    return INCIDENTS[-20:]


# ----- Individual actions (each returns (status, detail)) -----

def block_ip(source_ip: str):
    if not source_ip or source_ip == "unknown":
        return "skipped", "source IP unknown"
    try:
        existing = ""
        if os.path.exists(BLOCKLIST_PATH):
            existing = open(BLOCKLIST_PATH).read()
        if source_ip not in existing:
            with open(BLOCKLIST_PATH, "a") as f:
                f.write(f"deny {source_ip};\n")
        try:
            requests.post(WAF_RELOAD_URL, timeout=3)
        except Exception:
            pass
        return "ok", f"blocked {source_ip} at WAF"
    except Exception as e:
        return "failed", str(e)


def restart_container(name: str):
    if not client:
        return "failed", "docker client unavailable"
    try:
        client.containers.get(name).restart(timeout=10)
        return "ok", f"restarted {name}"
    except docker.errors.NotFound:
        return "failed", f"container {name} not found"
    except Exception as e:
        return "failed", str(e)


def check_integrity():
    try:
        r = requests.get(f"{PAYMENT_URL}/api/integrity", timeout=5)
        data = r.json()
        return ("ok", f"integrity ok ({data.get('users')} users)") if data.get("ok") else ("failed", "integrity compromised")
    except Exception as e:
        return "failed", str(e)


def run_action(name: str, req: RemediationRequest):
    if name == "block_ip":
        return block_ip(req.source_ip)
    if name == "restart_auth":
        return restart_container(AUTH_CONTAINER)
    if name == "restart_payment":
        return restart_container(PAYMENT_CONTAINER)
    if name == "check_integrity":
        return check_integrity()
    return "skipped", f"unknown action {name}"


def wait_healthy(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{PAYMENT_URL}/health", timeout=3).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def test_payment_ok():
    try:
        r = requests.post(f"{PAYMENT_URL}/api/payments/test", timeout=5)
        return r.status_code == 200 and r.json().get("ok") is True
    except Exception:
        return False


@app.post("/remediate", status_code=status.HTTP_200_OK)
def trigger_remediation(payload: RemediationRequest):
    """Autonomous recovery: runs the playbook for the incident type, and after
    each action verifies recovery with the payment test transaction. Stops as
    soon as the test succeeds. No human intervention required."""
    print(f"Remediation triggered! type={payload.type} reason={payload.reason} ip={payload.source_ip}")
    started = time.time()
    incident = {
        "incident_id": f"INC-{int(started)}",
        "type": payload.type,
        "source_ip": payload.source_ip,
        "status": "detected",
        "actions": [],
        "duration_ms": None,
    }
    INCIDENTS.append(incident)
    incident["status"] = "in_progress"

    plan = PLAYBOOKS.get(payload.type, PLAYBOOKS["anomaly"])
    for action in plan:
        t0 = time.time()
        st, detail = run_action(action, payload)
        incident["actions"].append(
            {"action": action, "status": st, "detail": detail, "duration_ms": int((time.time() - t0) * 1000)}
        )
        print(f"  action {action}: {st} ({detail})")
        if wait_healthy() and test_payment_ok():
            incident["status"] = "recovered"
            incident["duration_ms"] = int((time.time() - started) * 1000)
            return {"status": "SUCCESS", "incident": incident}

    incident["status"] = "failed"
    incident["duration_ms"] = int((time.time() - started) * 1000)
    raise HTTPException(status_code=500, detail="Remediation did not restore service")
