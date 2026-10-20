# Architecture — RESILIENCE-ALPHA

## Vue d'ensemble

```
PC Attaquant ──attaques──┐
                         ▼
        ┌──────────── PC Hôte (Docker Compose) ───────────┐
        │  [WAF Nginx + ModSecurity]  ← seul point d'entrée│
        │        │                                         │
        │   ┌────┴────┬───────────┐                        │
        │ [Front]  [Auth]    [Payment]── [PostgreSQL UUID]  │
        │                       │                          │
        │                 [Dashboard]                       │
        │  logs → [Promtail]→[Loki]   métriques→[Prometheus]│
        │              │                     │              │
        │         [Grafana]            [ml_engine]          │
        │                                    │ POST /remediate
        │                           [remediation-service]  │
        │                        bloque IP / redémarre / vérifie
        │                                    ▼              │
        │                     POST /api/payments/test = preuve │
        └───────────────────────────────────────────────────┘
```

## Les cinq piliers

| Pilier | Composant | Dossier |
| --- | --- | --- |
| DEV | auth, payment, remediation, dashboard | `services/` |
| INFRA | docker-compose, Prometheus/Loki/Grafana | `infrastructure/` |
| IA/DATA | détection d'anomalies (Isolation Forest) | `ml_engine/` |
| CYBER | WAF, SIEM (Loki), audit_logs, JWT bcrypt | `infrastructure/waf`, `services/auth-service` |
| TRANSFO | EBIOS, PCA/PRA, NIS2/DORA | `docs/` |

## Choix techniques

- PostgreSQL avec identifiants **UUID** ; tables `users`, `transactions`, `audit_logs`.
- Microservices FastAPI (`auth-service`, `payment-service`, `remediation-service`).
- Détection par **Isolation Forest** entraîné sur un baseline de trafic normal (pas de seuil fixe).
- Remédiation **déterministe** ; aucun LLM dans la boucle critique.

## Piste de durcissement

Le moteur de remédiation accède actuellement au socket Docker directement
(`/var/run/docker.sock`). Amélioration recommandée : passer par un
`docker-socket-proxy` pour restreindre les droits (principe du moindre privilège).
