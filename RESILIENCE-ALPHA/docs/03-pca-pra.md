# Plan de continuité et de reprise (PCA / PRA)

## Objectifs

| Indicateur | Cible | Mesuré par |
| --- | --- | --- |
| RTO (temps de reprise) | < 30 s | `duration_ms` du remediation-service |
| RPO (perte de données) | proche de 0 en démo | fréquence des transactions |
| Disponibilité visée | 99 % en conditions de démo | transaction de test continue |

## PCA — continuité pendant l'attaque

- Blocage de l'IP malveillante au WAF, trafic légitime préservé.
- Limitation de débit sur `/auth/login` et `/api/`.

## PRA — reprise après sinistre

| Sinistre | Procédure automatique | Repli manuel |
| --- | --- | --- |
| Service arrêté | redémarrage du conteneur `resilience_payment` | `docker restart` |
| Secret compromis | rotation du secret JWT + redémarrage auth | nouveau secret + redémarrage |
| Données supprimées | contrôle d'intégrité `/api/integrity` | restauration d'un dump PostgreSQL |

## Preuve de reprise

Après chaque action, le moteur appelle `POST /api/payments/test`. La reprise
n'est déclarée que lorsque cette transaction réussit. Le temps écoulé entre la
détection et ce succès est le RTO réel, affiché sur le dashboard.
