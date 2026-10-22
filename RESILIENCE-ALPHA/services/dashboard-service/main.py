import os
import time

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Resilience-Alpha Dashboard")

PAYMENT_URL = os.getenv("PAYMENT_URL", "http://resilience_payment:8002")
REMEDIATION_URL = os.getenv("REMEDIATION_URL", "http://resilience_remediation:8003")
AUTH_URL = os.getenv("AUTH_URL", "http://resilience_auth:8001")

HTML = open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8").read()


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/api/state")
def state():
    started = time.perf_counter()
    result = {
        "ts": time.time(),
        "payment_ok": False,
        "payment_latency_ms": None,
        "incident": None,
        "incidents": [],
        "components": {},
    }
    try:
        payment_started = time.perf_counter()
        r = requests.post(f"{PAYMENT_URL}/api/payments/test", timeout=3)
        result["payment_ok"] = r.status_code == 200 and r.json().get("ok") is True
        result["payment_latency_ms"] = round((time.perf_counter() - payment_started) * 1000, 1)
    except Exception:
        result["payment_ok"] = False
    try:
        r = requests.get(f"{REMEDIATION_URL}/incidents/latest", timeout=3)
        if r.status_code == 200 and r.json():
            result["incident"] = r.json()
    except Exception:
        pass
    try:
        r = requests.get(f"{REMEDIATION_URL}/incidents", timeout=3)
        if r.status_code == 200:
            result["incidents"] = r.json()
    except Exception:
        pass
    for name, url in (("payment", PAYMENT_URL), ("auth", AUTH_URL), ("remediation", REMEDIATION_URL)):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            result["components"][name] = response.status_code == 200
        except Exception:
            result["components"][name] = False
    result["components"]["dashboard"] = True
    result["poll_latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return JSONResponse(result)
