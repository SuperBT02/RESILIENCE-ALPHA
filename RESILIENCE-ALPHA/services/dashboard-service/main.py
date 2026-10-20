import os
import time

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Resilience-Alpha Dashboard")

PAYMENT_URL = os.getenv("PAYMENT_URL", "http://resilience_payment:8002")
REMEDIATION_URL = os.getenv("REMEDIATION_URL", "http://resilience_remediation:8003")

HTML = open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8").read()


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/api/state")
def state():
    result = {"ts": time.time(), "payment_ok": False, "incident": None}
    try:
        r = requests.post(f"{PAYMENT_URL}/api/payments/test", timeout=3)
        result["payment_ok"] = r.status_code == 200 and r.json().get("ok") is True
    except Exception:
        result["payment_ok"] = False
    try:
        r = requests.get(f"{REMEDIATION_URL}/incidents/latest", timeout=3)
        if r.status_code == 200 and r.json():
            result["incident"] = r.json()
    except Exception:
        pass
    return JSONResponse(result)
