# Conformité NIS2 / DORA

Chaque exigence est reliée à un élément réel du démonstrateur.

## NIS2 — mesures de gestion des risques (art. 21)

| Exigence | Mise en œuvre | Preuve |
| --- | --- | --- |
| Analyse de risques | EBIOS RM | `docs/02-ebios-rm.md` |
| Gestion des incidents | détection ML + journal du moteur | `remediation-service`, dashboard |
| Continuité et sauvegardes | PCA/PRA | `docs/03-pca-pra.md` |
| Sécurité des conteneurs | images officielles, non-root | Dockerfiles |
| Cryptographie et secrets | bcrypt, JWT, `.env` | `auth-service` |
| Journalisation | Loki + table `audit_logs` | Grafana |

## DORA — résilience opérationnelle

| Pilier | Mise en œuvre | Preuve |
| --- | --- | --- |
| Gestion du risque TIC | EBIOS + socle | `docs/02` |
| Gestion des incidents | remédiation tracée | journal des incidents |
| Tests de résilience | chaos engineering | `attacks/chaos.sh` |
| Continuité | RTO/RPO mesurés | `docs/03` |

## Recommandations à la direction

1. Passer l'accès Docker du moteur par un `docker-socket-proxy` (moindre privilège).
2. Externaliser les secrets dans un coffre (Vault) plutôt que `.env`.
3. Ajouter des sauvegardes PostgreSQL planifiées pour un vrai PRA.
4. Étendre la détection à d'autres signaux (géolocalisation des IP, empreintes).
5. Formaliser un test de résilience trimestriel (exigence DORA).
