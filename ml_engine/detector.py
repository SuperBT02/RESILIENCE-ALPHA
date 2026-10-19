import time
import requests
import numpy as np
from sklearn.ensemble import IsolationForest

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
REMEDIATION_WEBHOOK = "http://resilience_remediation:8003/remediate" # Will point to your remediation service

def fetch_prometheus_metric(query):
    """Fetches real-time metrics from Prometheus"""
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        data = response.json()
        result = data.get("data", {}).get("result", [])
        if result:
            return float(result[0]["value"][1])
    except Exception as e:
        print(f"Error communicating with Prometheus: {e}")
    return 0.0

def run_anomaly_detector():
    print("Starting Resilience-Alpha ML Anomaly Detector...")
    
    # Baseline training data simulation (Normal traffic patterns)
    # In production, you can train this dynamically or load a pre-fitted model
    X_train = np.array([
        [5.0, 10.0],   # Normal CPU %, Normal Request Rate
        [8.0, 15.0],
        [6.0, 12.0],
        [7.0, 11.0],
        [4.0, 9.0]
    ])
    
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(X_train)

    while True:
        # Pull live metrics from Prometheus (e.g., CPU load or request rates)
        # Using a generic request count or container metric query
        current_cpu = fetch_prometheus_metric('rate(container_cpu_usage_seconds_total{container_name="resilience_backend"}[1m])') * 100
        current_reqs = fetch_prometheus_metric('sum(rate(http_requests_total[1m]))')

        current_data = np.array([[current_cpu, current_reqs]])
        
        # Predict: 1 = Normal, -1 = Anomaly/Attack
        prediction = model.predict(current_data)
        
        print(f"Metrics -> CPU: {current_cpu:.2f}%, Reqs: {current_reqs:.2f} | Status: {'NORMAL' if prediction[0] == 1 else 'ANOMALY DETECTED!'}")

        if prediction[0] == -1:
            print("🚨 Attack detected by ML model! Triggering automated remediation...")
            trigger_remediation()

        time.sleep(5)  # Check every 5 seconds

def trigger_remediation():
    try:
        # Notify the remediation microservice to fix the system autonomously
        response = requests.post(REMEDIATION_WEBHOOK, json={"reason": "ML_ANOMALY_DETECTED"})
        print(f"Remediation triggered: {response.status_code}")
    except Exception as e:
        print(f"Failed to reach remediation service: {e}")

if __name__ == "__main__":
    time.sleep(10) # Wait for Prometheus to start up
    run_anomaly_detector()