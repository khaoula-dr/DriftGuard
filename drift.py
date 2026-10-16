#!/usr/bin/env python3
"""DriftGuard : détection de dérive Terraform.

Usage : python3 drift.py check
Aucune écriture sur les ressources métier. Codes de sortie :
0 = rien à signaler, 2 = dérive ou alerte, 1 = erreur (rapport d'erreur écrit).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from driftguard.plan_parser import extract_code_changes, extract_drifts
from driftguard.rules import CLASS_LABELS, classify, classify_plan_changes

REGION = "eu-north-1"  # ADR-002
ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"  # jamais versionné


class DriftGuardError(Exception):
    """Erreur de détection : arrêt immédiat, diagnostic dans le rapport."""


def _run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)


def _short(text: str, limit: int = 300) -> str:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return " | ".join(lines[:3])[:limit]


def _aws_json(args, env):
    result = _run(["aws", *args, "--region", REGION, "--output", "json"], env)
    if result.returncode != 0:
        raise DriftGuardError(f"aws {' '.join(args[:2])} a échoué : {_short(result.stderr)}")
    return json.loads(result.stdout)


def _assume_role(role_name: str) -> dict:
    """Assume le rôle (drift-reader par défaut) et renvoie l'environnement à utiliser."""
    account = _aws_json(["sts", "get-caller-identity"], os.environ.copy())["Account"]
    creds = _aws_json(
        ["sts", "assume-role",
         "--role-arn", f"arn:aws:iam::{account}:role/{role_name}",
         "--role-session-name", "driftguard-check"],
        os.environ.copy(),
    )["Credentials"]
    env = os.environ.copy()
    env.update({
        "AWS_ACCESS_KEY_ID": creds["AccessKeyId"],
        "AWS_SECRET_ACCESS_KEY": creds["SecretAccessKey"],
        "AWS_SESSION_TOKEN": creds["SessionToken"],
        "AWS_DEFAULT_REGION": REGION,
    })
    return env


def _git_state() -> dict:
    commit = _run(["git", "rev-parse", "HEAD"])
    if commit.returncode != 0:
        raise DriftGuardError("dépôt Git introuvable : impossible de fixer le commit de référence")
    dirty = bool(_run(["git", "status", "--porcelain"]).stdout.strip())
    return {"commit": commit.stdout.strip(), "clean": not dirty}


def _terraform_plan_json(env):
    """Plan sans verrou d'écriture (-lock=false) puis conversion en JSON."""
    with tempfile.TemporaryDirectory(prefix="driftguard-") as tmp:
        planfile = str(Path(tmp) / "plan.bin")  # supprimé en fin d'analyse
        plan = _run(["terraform", "-chdir=terraform", "plan", "-lock=false", "-input=false",
                     "-no-color", "-detailed-exitcode", "-out", planfile], env)
        if plan.returncode not in (0, 2):
            raise DriftGuardError(f"terraform plan a échoué : {_short(plan.stderr or plan.stdout)}")
        show = _run(["terraform", "-chdir=terraform", "show", "-json", planfile], env)
        if show.returncode != 0:
            raise DriftGuardError(f"terraform show a échoué : {_short(show.stderr)}")
        return json.loads(show.stdout), plan.returncode


def _write_report(report: dict) -> Path:
    REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS / f"drift-report-{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _fmt(value) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 80 else text[:77] + "..."


def _tag(item: dict) -> str:
    return f"[{CLASS_LABELS[item['class']]} | risque {item['risk']} | {item['action']}]"


def cmd_check(args) -> int:
    report = {
        "analysis_id": str(uuid.uuid4()),
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "region": REGION,
        "aws_identity": None,
        "git": None,
        "classification_definitive": False,
        "terraform_exit_code": None,
        "status": "error",
        "drifts": [],
        "code_changes": [],
        "alerts": [],
        "errors": [],
    }
    try:
        env = os.environ.copy() if args.no_assume else _assume_role(args.role)
        report["aws_identity"] = _aws_json(["sts", "get-caller-identity"], env)["Arn"]
        report["git"] = _git_state()
        plan, code = _terraform_plan_json(env)
    except DriftGuardError as error:
        report["errors"].append(str(error))
        path = _write_report(report)
        print(f"ERREUR : {error}\nDiagnostic enregistré : {path}", file=sys.stderr)
        return 1

    report["terraform_exit_code"] = code
    report["classification_definitive"] = report["git"]["clean"]
    report["drifts"] = [{**d, **classify(d)} for d in extract_drifts(plan)]
    report["code_changes"] = extract_code_changes(plan, {d["resource"] for d in report["drifts"]})
    report["alerts"] = classify_plan_changes(report["code_changes"])
    report["status"] = ("drift_detected" if report["drifts"]
                        else "alert" if report["alerts"] else "clean")
    path = _write_report(report)

    identity = report["aws_identity"].split("/")
    print(f"Identité : {identity[-2]}/{identity[-1]}")
    print(f"Commit de référence : {report['git']['commit'][:8]}")
    if not report["git"]["clean"]:
        print("ATTENTION : modifications non validées dans le dépôt, classification non définitive.")
    if not report["drifts"]:
        print("Aucune dérive détectée.")
    for drift in report["drifts"]:
        if drift["kind"] == "deleted":
            print(f"- {drift['resource']} : {drift['observed']}  {_tag(drift)}")
        else:
            print(f"~ {drift['resource']}  {drift['attribute']} : "
                  f"{_fmt(drift['expected'])} -> {_fmt(drift['observed'])}  {_tag(drift)}")
    for alert in report["alerts"]:
        print(f"! {alert['resource']} : {alert['reason']}  {_tag(alert)}")
    pending = [c for c in report["code_changes"]
               if not c["explained_by_drift"] and c["resource"] not in {a["resource"] for a in report["alerts"]}]
    if pending:
        print(f"Changements de code non appliqués : {', '.join(c['resource'] for c in pending)}")
    print(f"Rapport : {path}")
    return 2 if (report["drifts"] or report["alerts"]) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="drift.py", description="DriftGuard : détection de dérive")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="détecte les dérives et écrit un rapport JSON (lecture seule)")
    check.add_argument("--role", default="drift-reader", help="rôle IAM assumé (défaut : drift-reader)")
    check.add_argument("--no-assume", action="store_true",
                       help="utiliser l'identité courante, sans assumer de rôle (diagnostic)")
    args = parser.parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
