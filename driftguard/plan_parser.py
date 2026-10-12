"""Lecture du plan Terraform au format JSON : extraction des dérives.

Fonctions pures, sans appel AWS : testables hors ligne (tests/test_plan_parser.py).
"""
from __future__ import annotations

from typing import Any

# Attributs bruyants ignorés (liste documentée dans docs/journal.md).
# Règle : ne jamais y mettre une propriété de sécurité qu'aucune autre
# ressource suivie ne couvre.
EXCLUDED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"tags_all"},                  # doublon de "tags"
    "aws_iam_role": {"inline_policy"},  # politique suivie par aws_iam_role_policy
}

# Attributs dont la valeur n'est jamais écrite dans le rapport
MASKED_ATTRIBUTES = {"user_data", "user_data_base64", "password_data"}
MASK = "(masqué)"


def _top(path: str) -> str:
    return path.split(".")[0].split("[")[0]


def _sub(sensitive: Any, key: Any) -> Any:
    if sensitive is True:
        return True
    if isinstance(sensitive, dict):
        return sensitive.get(key, False)
    if isinstance(sensitive, list) and isinstance(key, int) and key < len(sensitive):
        return sensitive[key]
    return False


def flatten(value: Any, sensitive: Any = False, prefix: str = "") -> dict[str, tuple]:
    """Aplatit un objet JSON en {chemin: (valeur, sensible)}. Conteneurs vides ignorés."""
    out: dict[str, tuple] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten(item, _sub(sensitive, key), path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.update(flatten(item, _sub(sensitive, index), f"{prefix}[{index}]"))
    else:
        out[prefix] = (value, sensitive is True)
    return out


def is_excluded(resource_type: str, path: str) -> bool:
    top = _top(path)
    return top in EXCLUDED_ATTRIBUTES["*"] or top in EXCLUDED_ATTRIBUTES.get(resource_type, set())


def _entry(address, resource_type, attribute, expected, observed, kind) -> dict:
    return {
        "source": "terraform",
        "resource": address,
        "resource_type": resource_type,
        "attribute": attribute,
        "expected": expected,   # valeur connue de Terraform (état = code appliqué)
        "observed": observed,   # valeur réelle dans AWS
        "kind": kind,
        "class": "unclassified",                    # règles : US-7
        "risk": None,                               # règles : US-7
        "attribution": {"state": "not_checked"},    # CloudTrail : US-10
        "correction": {"state": "not_attempted"},   # correction : US-11
        "errors": [],
    }


def extract_drifts(plan: dict) -> list[dict]:
    """Dérives = section resource_drift (modifications hors Terraform), attribut par attribut."""
    drifts: list[dict] = []
    for item in plan.get("resource_drift") or []:
        address, rtype = item["address"], item["type"]
        change = item["change"]
        if change.get("actions") == ["delete"]:
            drifts.append(_entry(address, rtype, None, "(ressource présente)",
                                 "(ressource supprimée)", "deleted"))
            continue
        before = flatten(change.get("before") or {}, change.get("before_sensitive", False))
        after = flatten(change.get("after") or {}, change.get("after_sensitive", False))
        for path in sorted(set(before) | set(after)):
            if is_excluded(rtype, path):
                continue
            b_val, b_sens = before.get(path, (None, False))
            a_val, a_sens = after.get(path, (None, False))
            if b_val == a_val:
                continue
            masked = b_sens or a_sens or _top(path) in MASKED_ATTRIBUTES
            drifts.append(_entry(address, rtype, path,
                                 MASK if masked else b_val,
                                 MASK if masked else a_val, "modified"))
    return drifts


def extract_code_changes(plan: dict, drifted_addresses: set[str]) -> list[dict]:
    """Actions proposées par le plan (resource_changes).

    explained_by_drift = True : l'action ne fait que ramener la ressource à l'état du code.
    False : le code a changé sans avoir été appliqué.
    """
    changes = []
    for item in plan.get("resource_changes") or []:
        actions = item["change"]["actions"]
        if actions in (["no-op"], ["read"]):
            continue
        changes.append({
            "resource": item["address"],
            "actions": actions,
            "explained_by_drift": item["address"] in drifted_addresses,
        })
    return changes
