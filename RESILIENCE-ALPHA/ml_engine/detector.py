import os
import time

import requests
import numpy as np
from sklearn.ensemble import IsolationForest

# Inside the Docker network Prometheus is reachable by its container name.
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://resilience_prometheus:9090/api/v1/query")
REMEDIATION_WEBHOOK = os.getenv("REMEDIATION_WEBHOOK", "http://resilience_remediation:8003/remediate")

WINDOW = int(os.getenv("DETECT_WINDOW_SECONDS", "10"))
STREAK = int(os.getenv("DETECT_STREAK", "2"))
COOLDOWN = int(os.getenv("DETECT_COOLDOWN_SECONDS", "60"))

# Feature order kept explicit so we can tell WHICH signal deviated the most and
# qualify the incident type from it (detection itself is done by the ML model).
FEATURES = ["req_rate", "err_4xx", "err_5xx", "p95_ms"]
FEATURE_TO_TYPE = {
    "err_4xx": "bruteforce",   # spike of 401/4xx on auth = brute force / scan
    "err_5xx": "service_down",
    "p95_ms": "flood",
    "req_rate": "flood",
}


def fetch(query: str) -> float:
    """Fetches a single scalar metric from Prometheus."""
    try:
        r = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=3)
        result = r.json().get("data", {}).get("result", [])
        if result:
            return float(result[0]["value"][1])
    except Exception as e:
        print(f"Error communicating with Prometheus: {e}")
    return 0.0


def fetch_source_ip(window: str) -> str:
    """Return the most active source IP for the signal that drove the incident."""
    queries = (
        f'topk(1, sum by (source_ip) (rate(auth_login_failures_total[{window}])))',
        f'topk(1, sum by (source_ip) (rate(payment_requests_by_source_ip_total[{window}])))',
    )
    for query in queries:
        try:
            r = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=3)
            result = r.json().get("data", {}).get("result", [])
            if result and result[0].get("metric", {}).get("source_ip"):
                return result[0]["metric"]["source_ip"]
        except (requests.RequestException, ValueError, KeyError, IndexError) as e:
            print(f"Error reading source IP from Prometheus: {e}")
    return "unknown"


def read_window():
    w = f"{WINDOW}s"
    return {
        "req_rate": fetch(f"sum(rate(http_requests_total[{w}]))"),
        "err_4xx": fetch(f'sum(rate(http_requests_total{{status=~"4.."}}[{w}]))'),
        "err_5xx": fetch(f'sum(rate(http_requests_total{{status=~"5.."}}[{w}]))'),
        "p95_ms": fetch(f"histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[{w}]))) * 1000"),
    }


def run_anomaly_detector():
    print("Starting Resilience-Alpha ML Anomaly Detector (Isolation Forest)...")

    # Collect a short live baseline of NORMAL traffic, then fit the model on it.
    # Falls back to a small synthetic baseline if Prometheus is not ready yet.
    baseline = []
    print("Collecting baseline (normal traffic)...")
    for _ in range(20):
        baseline.append([read_window()[f] for f in FEATURES])
        time.sleep(WINDOW / 4)
    X_train = np.array(baseline) if len(baseline) >= 5 else np.array([[5, 0, 0, 40], [8, 0, 0, 45], [6, 0, 0, 38]])

    scaler_mean = X_train.mean(axis=0)
    scaler_std = X_train.std(axis=0) + 1e-6
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    model.fit((X_train - scaler_mean) / scaler_std)
    print(f"Model trained on {len(X_train)} normal windows.")

    streak = 0
    last_alert = 0.0
    while True:
        feats = read_window()
        x = np.array([[feats[f] for f in FEATURES]])
        xs = (x - scaler_mean) / scaler_std
        prediction = model.predict(xs)[0]  # 1 = normal, -1 = anomaly
        score = float(model.decision_function(xs)[0])
        status = "NORMAL" if prediction == 1 else "ANOMALY DETECTED!"
        print(f"Metrics -> {feats} | score={score:.3f} | {status}")

        if prediction == -1:
            streak += 1
            if streak >= STREAK and (time.time() - last_alert) > COOLDOWN:
                top_feature = FEATURES[int(np.argmax(np.abs(xs[0])))]
                itype = FEATURE_TO_TYPE.get(top_feature, "anomaly")
                print(f"Attack detected! type={itype} (driven by {top_feature})")
                trigger_remediation(itype, score)
                last_alert = time.time()
                streak = 0
        else:
            streak = 0
        time.sleep(WINDOW)


def trigger_remediation(itype: str, score: float):
    try:
        source_ip = fetch_source_ip(f"{WINDOW}s")
        r = requests.post(
            REMEDIATION_WEBHOOK,
            json={"reason": "ML_ANOMALY_DETECTED", "type": itype, "source_ip": source_ip},
            timeout=5,
        )
        print(f"Remediation triggered: HTTP {r.status_code}, source_ip={source_ip}")
    except Exception as e:
        print(f"Failed to reach remediation service: {e}")


if __name__ == "__main__":
    time.sleep(15)  # wait for Prometheus and services to start
    run_anomaly_detector()
