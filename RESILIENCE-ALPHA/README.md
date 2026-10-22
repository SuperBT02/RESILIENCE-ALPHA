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
  → l'IP dominante est récupérée depuis les métriques par source
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

## Tester depuis un deuxième PC

Les scripts d'attaque doivent être utilisés uniquement contre votre propre
environnement de laboratoire RESILIENCE-ALPHA.

### Préparer le PC Hôte Docker

Récupérer son adresse IPv4 :

```powershell
ipconfig
```

Autoriser le WAF HTTP dans le pare-feu Windows (PowerShell administrateur) :

```powershell
New-NetFirewallRule `
  -DisplayName "RESILIENCE-ALPHA WAF HTTP" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 80 `
  -Action Allow `
  -Profile Private
```

Démarrer la stack :

```powershell
docker compose up -d --build
docker compose ps
```

### Préparer le PC Attaquant

Le PC attaquant doit disposer de Linux, macOS ou WSL/Git Bash avec `curl`.
Depuis la racine du projet :

```bash
cd attacks
chmod +x *.sh
TARGET=192.168.1.100       # remplacer par l'IP du PC Hôte
curl -i "http://$TARGET/"
```

Tester l'accès à l'authentification :

```bash
curl -i -X POST "http://$TARGET/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice_merchant","password":"wrong-password"}'
```

Une réponse `401 Unauthorized` confirme que la requête atteint le service.

### Lancer les scénarios

Brute-force contrôlé, recommandé pour tester la détection ML :

```bash
./bruteforce.sh "$TARGET" 180
```

Flood HTTP contrôlé (durée, puis nombre de requêtes parallèles) :

```bash
./flood.sh "$TARGET" 30 20
```

Tentatives d'injection SQL destinées à être bloquées par le WAF :

```bash
./injection.sh "$TARGET" 60
```

Le lanceur global peut aussi être utilisé :

```bash
./run.sh bruteforce "$TARGET"
./run.sh flood "$TARGET"
./run.sh injection "$TARGET"
```

Le scénario `chaos` agit directement sur Docker et doit être exécuté sur le
PC Hôte, pas sur le PC Attaquant :

```bash
./chaos.sh stop
```

### Observer et vérifier la récupération

Sur le PC Hôte, ouvrir le dashboard :

```text
http://localhost:8090/
```

Suivre les logs dans deux terminaux :

```powershell
docker logs -f resilience_ml
docker logs -f resilience_remediation
```

Vérifier le dernier incident et l'historique :

```powershell
Invoke-RestMethod http://localhost:8003/incidents/latest |
  ConvertTo-Json -Depth 10

Invoke-RestMethod http://localhost:8003/incidents |
  ConvertTo-Json -Depth 10
```

Vérifier l'IP source détectée par Prometheus :

```powershell
$query = 'topk(1, sum by (source_ip) (rate(auth_login_failures_total[120s])))'
$url = "http://localhost:9090/api/v1/query?query=$([uri]::EscapeDataString($query))"
Invoke-RestMethod -Uri $url | ConvertTo-Json -Depth 10
```

Vérifier la blocklist WAF :

```powershell
docker exec resilience_waf sh -c "cat /shared/blocklist.conf"
```

Le résultat attendu est :

```text
attaque depuis le PC Attaquant
→ IP source visible dans Prometheus
→ incident affiché dans le dashboard
→ remédiation automatique
→ transaction de preuve réussie
→ dashboard revenu au vert
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
