import os
import random
import time

import requests

# Generates legitimate traffic through the WAF so the ML baseline is realistic
# and the service state is visible before/during/after an incident (useful for
# the Clip Chrono).
BASE = os.getenv("TARGET_URL", "http://resilience_waf:8080")
USERS = [("alice_merchant", "alice-demo-2026"), ("bob_customer", "bob-demo-2026")]


def one_client():
    user, pw = random.choice(USERS)
    # 2% wrong passwords = normal errors.
    pw_try = pw if random.random() > 0.02 else pw + "x"
    try:
        r = requests.post(f"{BASE}/auth/login", json={"username": user, "password": pw_try}, timeout=5)
        if r.status_code == 200 and random.random() > 0.3:
            requests.post(f"{BASE}/api/payments/test", timeout=5)
    except Exception:
        pass


def main():
    print(f"Traffic generator -> {BASE}")
    while True:
        one_client()
        time.sleep(random.choice([0.4, 0.8, 1.2, 1.5, 2.0, 3.0]))


if __name__ == "__main__":
    time.sleep(10)
    main()
