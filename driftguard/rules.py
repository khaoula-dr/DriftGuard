"""Règles de classification des écarts : centralisées ici, testées sans appel AWS.

Principe : un écart n'est corrigé automatiquement (action "auto_fix") que s'il s'agit
d'un tag géré, non sensible, sur un type de ressource que drift-fixer a le droit de
taguer. Tout le reste passe par une confirmation ou une alerte seule.
"""
from __future__ import annotations

MANAGED_TAG_KEYS = {"Project", "Environment", "ManagedBy"}
# Tags qui interviennent dans des politiques IAM ou SSM : jamais corrigés automatiquement
SECURITY_TAG_KEYS = {"Project"}
# Types que drift-fixer peut taguer (voir terraform/iam.tf)
FIXER_TAGGABLE_TYPES = {"aws_instance", "aws_security_group", "aws_s3_bucket"}
SECURITY_TYPE_PREFIXES = (
    "aws_security_group", "aws_vpc_security_group", "aws_iam_",
    "aws_s3_bucket_public_access_block", "aws_s3_bucket_policy",
)

CLASS_LABELS = {
    "metadata": "Métadonnées",
    "to_analyze": "À analyser",
    "network_security": "Réseau et sécurité",
    "infrastructure": "Infrastructure",
    "system": "Système",
    "destructive": "Destructive",
    "high_risk": "Risque élevé",
    "indeterminate": "Indéterminé",
    "unclassified": "Non classé",
}


def _result(cls: str, risk: str, action: str, reason: str) -> dict:
    return {"class": cls, "risk": risk, "action": action, "reason": reason}


def _classify_tag(resource_type: str, key: str, drift: dict) -> dict:
    if key not in MANAGED_TAG_KEYS:
        return _result("to_analyze", "medium", "confirm",
                       "tag hors des clés gérées : drift-fixer n'a pas le droit de l'écrire ni de le supprimer")
    if key in SECURITY_TAG_KEYS:
        return _result("to_analyze", "high", "confirm",
                       "ce tag intervient dans des politiques IAM et SSM")
    if resource_type not in FIXER_TAGGABLE_TYPES:
        return _result("to_analyze", "medium", "confirm",
                       "drift-fixer ne peut pas taguer ce type de ressource")
    if drift.get("expected") is None:
        return _result("to_analyze", "medium", "confirm",
                       "tag ajouté à la main : le retirer exige une suppression")
    return _result("metadata", "low", "auto_fix", "tag géré modifié ou manquant")


def classify(drift: dict) -> dict:
    """Renvoie class, risk, action et reason pour un écart de dérive."""
    if drift.get("source") == "ansible":
        return _result("system", "medium", "confirm_then_ansible", "configuration du serveur modifiée")
    if drift.get("kind") == "deleted":
        return _result("destructive", "critical", "alert_only", "ressource supprimée hors Terraform")
    attribute = drift.get("attribute") or ""
    resource_type = drift["resource_type"]
    if attribute.startswith("tags."):
        return _classify_tag(resource_type, attribute[len("tags."):], drift)
    if resource_type.startswith(SECURITY_TYPE_PREFIXES):
        return _result("network_security", "high", "alert_and_confirm",
                       "propriété réseau ou sécurité modifiée")
    return _result("infrastructure", "medium", "alert_and_confirm", "propriété de ressource modifiée")


def classify_plan_changes(changes: list[dict]) -> list[dict]:
    """Alertes sur les actions proposées par le plan : suppression ou remplacement."""
    alerts = []
    for change in changes:
        actions = set(change["actions"])
        if "delete" in actions and "create" in actions:
            cls, risk, reason = "high_risk", "high", "le plan propose de remplacer la ressource"
        elif "delete" in actions:
            cls, risk, reason = "destructive", "critical", "le plan propose de supprimer la ressource"
        else:
            continue
        alerts.append({
            "resource": change["resource"], "actions": change["actions"],
            "class": cls, "risk": risk, "action": "alert_only", "reason": reason,
            "explained_by_drift": change["explained_by_drift"],
        })
    return alerts
