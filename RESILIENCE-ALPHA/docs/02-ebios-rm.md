# Analyse de risques — EBIOS Risk Manager

À valider par les coachs dès le lundi. Chaque scénario opérationnel correspond à
une attaque réellement implémentée (`attacks/`).

## Atelier 1 — Cadrage et socle

**Valeurs métier** : disponibilité du paiement, intégrité des transactions, confidentialité des identifiants.
**Biens supports** : WAF, auth-service, payment-service, PostgreSQL, réseau du hotspot.
**Socle** : durcissement conteneurs, JWT + bcrypt, journalisation (Loki + table `audit_logs`).

## Atelier 2 — Sources de risque

| Source | Objectif |
| --- | --- |
| Cybercriminel opportuniste | détourner des fonds, revendre des accès |
| Acteur de déni de service | rendre le service indisponible |
| Attaquant interne | altérer ou supprimer des données |

## Atelier 3 — Scénarios stratégiques

| Événement redouté | Gravité |
| --- | --- |
| Interruption prolongée du paiement | Critique |
| Falsification de transactions | Critique |
| Vol d'identifiants | Majeure |

## Atelier 4 — Scénarios opérationnels (= nos attaques)

| Scénario | Détection | Réaction automatique |
| --- | --- | --- |
| Brute force | ML sur le pic de 401 (auth) | blocage IP + redémarrage auth |
| Injection SQL | WAF + ML sur 4xx | blocage IP + contrôle d'intégrité |
| Déni de service | ML sur latence/5xx | limitation de débit + redémarrage |
| Sabotage (panne/corruption) | /health + ML sur 5xx | redémarrage + vérification |

## Atelier 5 — Traitement du risque

| Risque | Vraisemblance | Gravité | Traitement | Résiduel |
| --- | --- | --- | --- | --- |
| Interruption | Forte | Critique | détection + remédiation auto (RTO < 30 s) | Modéré |
| Falsification | Moyenne | Critique | requêtes paramétrées + WAF | Faible |
| Vol d'identifiants | Moyenne | Majeure | bcrypt + JWT court + rotation | Faible |
