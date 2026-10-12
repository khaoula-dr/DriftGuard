"""Garde-fous statiques sur les politiques IAM (aucun accès AWS requis).

Ils échouent si quelqu'un élargit par erreur les droits de drift-reader
ou de drift-fixer dans terraform/iam.tf.
"""
import re
from pathlib import Path

IAM_TF = Path(__file__).resolve().parents[1] / "terraform" / "iam.tf"

ACTIONS_FIXER_AUTORISEES = {
    "ec2:DescribeInstances",
    "ec2:DescribeTags",
    "ec2:DescribeSecurityGroups",
    "ec2:CreateTags",
    "s3:GetBucketTagging",
    "s3:PutBucketTagging",
}

VERBES_D_ECRITURE = re.compile(
    r"^(ec2|s3|iam|ssm):(Create|Put|Delete|Terminate|Authorize|Revoke|Modify|Run|Start|Stop|Update|Attach|Detach)"
)


def _bloc_politique(nom: str) -> str:
    texte = IAM_TF.read_text(encoding="utf-8")
    debut = texte.index(f'resource "aws_iam_role_policy" "{nom}"')
    fin = texte.find('\nresource "', debut + 1)
    return texte[debut:] if fin == -1 else texte[debut:fin]


def _actions(bloc: str) -> set:
    trouvees = re.findall(r'"([a-z0-9]+:[A-Za-z*]+)"', bloc)
    return {a for a in trouvees if not a.startswith("aws:")}


def test_aucune_action_joker():
    texte = IAM_TF.read_text(encoding="utf-8")
    assert not re.search(r'Action\s*=\s*"\*"', texte)


def test_fixer_limite_aux_tags():
    actions = _actions(_bloc_politique("fixer"))
    assert actions <= ACTIONS_FIXER_AUTORISEES, actions - ACTIONS_FIXER_AUTORISEES


def test_fixer_sans_suppression():
    actions = _actions(_bloc_politique("fixer"))
    assert not any("Delete" in a or "Terminate" in a for a in actions)


def test_reader_sans_ecriture():
    ecritures = [a for a in _actions(_bloc_politique("reader")) if VERBES_D_ECRITURE.match(a)]
    assert ecritures == []


def test_reader_ne_peut_lancer_que_le_document_de_controle():
    bloc = _bloc_politique("reader")
    assert bloc.count("ssm:SendCommand") == 2
    assert "AWS-RunShellScript" not in bloc
