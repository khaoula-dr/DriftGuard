"""Tests des règles de classification : aucun accès AWS."""
from driftguard.rules import FIXER_TAGGABLE_TYPES, classify, classify_plan_changes


def _drift(rtype, attribute, expected="lab", observed="prod", kind="modified", source="terraform"):
    return {"source": source, "resource": f"{rtype}.x", "resource_type": rtype,
            "attribute": attribute, "expected": expected, "observed": observed, "kind": kind}


def test_tag_gere_modifie_est_corrige_automatiquement():
    r = classify(_drift("aws_instance", "tags.Environment"))
    assert (r["class"], r["risk"], r["action"]) == ("metadata", "low", "auto_fix")


def test_tag_gere_manquant_est_corrige_automatiquement():
    r = classify(_drift("aws_instance", "tags.ManagedBy", expected="terraform", observed=None))
    assert r["action"] == "auto_fix"


def test_tag_ajoute_a_la_main_demande_confirmation():
    r = classify(_drift("aws_instance", "tags.Rogue", expected=None, observed="1"))
    assert (r["class"], r["action"]) == ("to_analyze", "confirm")


def test_tag_de_securite_jamais_corrige_automatiquement():
    r = classify(_drift("aws_instance", "tags.Project", expected="driftguard", observed="autre"))
    assert (r["class"], r["risk"], r["action"]) == ("to_analyze", "high", "confirm")


def test_tag_sur_type_non_taggable_par_le_fixer():
    r = classify(_drift("aws_iam_role", "tags.Environment"))
    assert r["action"] == "confirm"


def test_security_group_modifie():
    r = classify(_drift("aws_security_group", "ingress[0].from_port", expected=0, observed=22))
    assert (r["class"], r["risk"], r["action"]) == ("network_security", "high", "alert_and_confirm")


def test_propriete_d_instance_modifiee():
    r = classify(_drift("aws_instance", "instance_type", expected="t3.micro", observed="t3.large"))
    assert (r["class"], r["action"]) == ("infrastructure", "alert_and_confirm")


def test_ressource_supprimee_alerte_seule():
    r = classify(_drift("aws_instance", None, kind="deleted"))
    assert (r["class"], r["risk"], r["action"]) == ("destructive", "critical", "alert_only")


def test_ecart_ansible_est_systeme():
    r = classify(_drift("nginx", "/etc/nginx/nginx.conf", source="ansible"))
    assert r["class"] == "system"


def test_remplacement_propose_par_le_plan_est_une_alerte_seule():
    alertes = classify_plan_changes([
        {"resource": "aws_instance.web", "actions": ["delete", "create"], "explained_by_drift": False}])
    assert len(alertes) == 1
    assert (alertes[0]["class"], alertes[0]["action"]) == ("high_risk", "alert_only")


def test_suppression_proposee_par_le_plan_est_destructive():
    alertes = classify_plan_changes([
        {"resource": "aws_s3_bucket.app", "actions": ["delete"], "explained_by_drift": False}])
    assert alertes[0]["class"] == "destructive"


def test_mise_a_jour_simple_ne_declenche_pas_d_alerte():
    assert classify_plan_changes([
        {"resource": "aws_instance.web", "actions": ["update"], "explained_by_drift": True}]) == []


def test_auto_fix_reserve_aux_tags_geres():
    # Aucune propriété hors tags ne doit jamais ouvrir la correction automatique
    cas = [("aws_instance", "instance_type"), ("aws_security_group", "ingress[0].from_port"),
           ("aws_s3_bucket", "force_destroy"), ("aws_iam_role", "assume_role_policy"),
           ("aws_instance", "iam_instance_profile")]
    for rtype, attribut in cas:
        assert classify(_drift(rtype, attribut))["action"] != "auto_fix"
    assert classify(_drift("aws_instance", None, kind="deleted"))["action"] != "auto_fix"
    assert FIXER_TAGGABLE_TYPES == {"aws_instance", "aws_security_group", "aws_s3_bucket"}
