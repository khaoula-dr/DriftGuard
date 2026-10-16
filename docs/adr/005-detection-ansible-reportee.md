# ADR-005 : Détection de la configuration serveur (Ansible via SSM) reportée en extension

- **Statut** : reportée (décision du 2026-10-12).
- **Contexte** : le temps disponible ne permet pas de livrer toutes les stories du cahier des charges v4.0 avec la qualité attendue (tests, documentation, démonstration). Le détecteur Ansible (US-8, US-15) est la partie la plus coûteuse (8 points sur 49 avec ses vérifications) et la moins différenciante : la valeur du projet tient à la séparation des droits IAM, à l'attribution CloudTrail et à la correction bornée.
- **Options étudiées** : (a) livrer le détecteur Ansible complet ; (b) le reporter et le présenter comme extension prévue ; (c) en livrer une version partielle non testée (rejetée : un résultat non vérifié contredit le principe « ne jamais confondre une probabilité avec une preuve »).
- **Décision** : (b).
- **Conséquences** :
  - Le projet détecte et corrige la dérive **d'infrastructure AWS** (Terraform). La dérive de configuration serveur n'est pas implémentée et n'est pas annoncée comme telle.
  - Conservé comme base de l'extension : playbook `ansible/playbook.yml` (vérifié par `ansible-lint` en CI), document SSM `driftguard-check`, droit `ssm:SendCommand` limité à ce seul document (tests N4 et P6), classe « Système » dans les règles.
  - Hors périmètre aussi : vérification HTTP 200 de Nginx (US-14). La vérification après correction reste un nouveau `drift.py check` sans écart (US-11).
- **Conception cible si reprise** : document SSM dédié exécutant Ansible en mode check ; comparaison de hachage du fichier de référence ; correction après confirmation, avec le profil opérateur et jamais avec `drift-fixer`.
