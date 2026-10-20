# RESILIENCE-ALPHA

Système d'information de paiement conteneurisé, capable d'encaisser une attaque
réelle et de se rétablir **sans intervention humaine** : détection par machine
learning, remédiation automatique, preuve par une transaction qui réussit après
l'incident.

Workshop M2 2026 — EPSI.

## La boucle cible

```
Attaque (PC Attaquant)
  → Prometheus (métriques) + Loki (logs)
  → ml_engine (Isolation Forest) détecte l'anomalie
  → POST /remediate au remediation-service
  → playbook : blocage IP / redémarrage / vérification
  → POST /api/payments/test réussit
  → le dashboard repasse au vert
```

## Démarrage rapide

Pré-requis sur le PC Hôte : Docker Desktop + WSL2, 16 Go de RAM.

```bash
cp .env.example .env          # puis éditer les mots de passe
docker compose up -d --build
```

Accès (remplacer `localhost` par l'IP du PC Hôte depuis un autre poste) :

| Service | URL |
| --- | --- |
| WAF / front | http://localhost/ |
| Dashboard de démo | http://localhost:8090/ |
| Grafana | http://localhost:3000/ (admin) |
| Prometheus | http://localhost:9090/ |

Comptes de démo : `alice_merchant` / `alice-demo-2026`, `bob_customer` / `bob-demo-2026`.

## Lancer une attaque (depuis le PC Attaquant)

```bash
./attacks/run.sh bruteforce <ip-pc-hote>
./attacks/chaos.sh stop        # panne provoquée (sur le PC Hôte, la plus fiable)
```

## Structure

```
RESILIENCE-ALPHA/
├── docker-compose.yml
├── services/
│   ├── auth-service/           # login JWT + bcrypt, audit (CYBER/DEV)
│   ├── payment-service/        # paiement + transaction de test (DEV)
│   ├── remediation-service/    # moteur de remédiation (DEV/INFRA)
│   ├── frontend-service/       # interface de paiement
│   ├── dashboard-service/      # supervision temps réel
│   └── traffic-generator/      # trafic légitime pour le ML
├── ml_engine/                  # détection d'anomalies (IA/DATA)
├── infrastructure/
│   ├── db/                     # schéma PostgreSQL (UUID)
│   ├── prometheus/ loki/ promtail/ grafana/   # observabilité + SIEM
│   └── waf/                    # Nginx + ModSecurity (CYBER)
├── attacks/                    # scripts Red Team
└── docs/                       # gouvernance : EBIOS, PCA/PRA, NIS2/DORA
```

## Sécurité du dépôt

- Aucun secret en clair : `.env` est ignoré par Git (seul `.env.example` est versionné).
- Les mots de passe de la base sont dans `.env`, pas dans le code.
