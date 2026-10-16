"""Tests du parseur de plan Terraform : aucun accès AWS, aucun terraform."""
from driftguard.plan_parser import (
    EXCLUDED_ATTRIBUTES,
    MASK,
    extract_code_changes,
    extract_drifts,
)


def _drift(address, rtype, before, after, actions=("update",)):
    return {
        "address": address,
        "type": rtype,
        "change": {
            "actions": list(actions),
            "before": before,
            "after": after,
            "before_sensitive": {},
            "after_sensitive": {},
        },
    }


def _plan_tag():
    avant = {"Environment": "lab", "Project": "driftguard"}
    apres = {"Environment": "prod", "Project": "driftguard"}
    return {
        "resource_drift": [_drift(
            "aws_instance.web", "aws_instance",
            {"tags": avant, "tags_all": avant}, {"tags": apres, "tags_all": apres})],
        "resource_changes": [{"address": "aws_instance.web", "change": {"actions": ["update"]}}],
    }


def test_tag_modifie_detecte():
    drifts = extract_drifts(_plan_tag())
    assert len(drifts) == 1
    d = drifts[0]
    assert d["resource"] == "aws_instance.web"
    assert d["attribute"] == "tags.Environment"
    assert (d["expected"], d["observed"]) == ("lab", "prod")


def test_tags_all_ignore():
    assert all("tags_all" not in d["attribute"] for d in extract_drifts(_plan_tag()))


def test_tag_ajoute_hors_terraform():
    plan = {"resource_drift": [_drift(
        "aws_instance.web", "aws_instance",
        {"tags": {"Project": "driftguard"}},
        {"tags": {"Project": "driftguard", "Rogue": "1"}})]}
    d = extract_drifts(plan)[0]
    assert d["attribute"] == "tags.Rogue"
    assert d["expected"] is None and d["observed"] == "1"


def test_bruit_inline_policy_exclu():
    plan = {"resource_drift": [_drift(
        "aws_iam_role.reader", "aws_iam_role",
        {"inline_policy": [{"name": "p", "policy": "a"}]},
        {"inline_policy": [{"name": "p", "policy": "b"}]})]}
    assert extract_drifts(plan) == []


def test_aucune_derive():
    assert extract_drifts({}) == []


def test_ressource_supprimee():
    plan = {"resource_drift": [_drift("aws_instance.web", "aws_instance",
                                      {"id": "i-1"}, None, actions=("delete",))]}
    drifts = extract_drifts(plan)
    assert len(drifts) == 1 and drifts[0]["kind"] == "deleted"


def test_user_data_masque():
    plan = {"resource_drift": [_drift(
        "aws_instance.web", "aws_instance",
        {"user_data": "#!/bin/bash secret"}, {"user_data": "autre"})]}
    d = extract_drifts(plan)[0]
    assert d["expected"] == MASK and d["observed"] == MASK


def test_propriete_de_securite_jamais_exclue():
    plan = {"resource_drift": [_drift(
        "aws_security_group.web", "aws_security_group",
        {"ingress": [{"from_port": 0, "cidr_blocks": []}]},
        {"ingress": [{"from_port": 22, "cidr_blocks": ["0.0.0.0/0"]}]})]}
    attributs = [d["attribute"] for d in extract_drifts(plan)]
    assert "ingress[0].from_port" in attributs


def test_code_changes_expliques_par_derive():
    plan = _plan_tag()
    plan["resource_changes"].append(
        {"address": "aws_s3_bucket.app", "change": {"actions": ["update"]}})
    plan["resource_changes"].append(
        {"address": "aws_iam_role.ec2", "change": {"actions": ["no-op"]}})
    drifts = extract_drifts(plan)
    changes = extract_code_changes(plan, {d["resource"] for d in drifts})
    par_adresse = {c["resource"]: c["explained_by_drift"] for c in changes}
    assert par_adresse == {"aws_instance.web": True, "aws_s3_bucket.app": False}


def test_liste_exclusion_sans_propriete_de_securite():
    interdits = {"ingress", "egress", "policy", "assume_role_policy",
                 "server_side_encryption_configuration", "security_groups",
                 "vpc_security_group_ids", "iam_instance_profile"}
    exclus = set().union(*EXCLUDED_ATTRIBUTES.values())
    assert exclus.isdisjoint(interdits)
