# ADR-001 : Exécution depuis le terminal, GitHub Actions sans accès AWS

- **Contexte** : une SCP interdit l'OIDC GitHub vers AWS.
- **Options étudiées** : (a) OIDC GitHub vers AWS (refusé par la SCP) ; (b) clés d'accès longue durée dans les secrets GitHub (risque inacceptable) ; (c) opérations AWS depuis le terminal, CI statique seulement.
- **Décision** : (c).
- **Conséquences** : la CI fait fmt, validate, ansible-lint et tests unitaires, sans aucun accès AWS. Les opérations AWS sont lancées par l'opérateur.
- **Validation** : connexion `aws login` fonctionnelle (2026-10-11) ; aucune clé longue durée créée.
