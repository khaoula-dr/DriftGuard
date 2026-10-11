# ADR-004 : State dans un bucket S3 dédié, lu sans verrou

- **Contexte** : drift-reader doit lire l'état sans pouvoir écrire.
- **Options étudiées** : state local (non reproductible) ; verrou avec droit d'écriture pour le lecteur (casse la lecture seule).
- **Décision** : bucket S3 dédié hors cycle de destruction, `use_lockfile = true`, plan du lecteur avec `-lock=false`.
- **Conséquences** : drift-reader n'a besoin que de la lecture sur le bucket ; risque limité à une lecture pendant une écriture concurrente (acceptable en lecture seule).
- **Validation** : test réussi le 2026-10-11 (state écrit, `terraform plan -lock=false` sans erreur).
