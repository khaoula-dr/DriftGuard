locals {
  account_id       = data.aws_caller_identity.current.account_id
  region           = "eu-north-1"
  state_bucket_arn = "arn:aws:s3:::driftguard-tfstate-${local.account_id}"
  managed_tag_keys = ["Project", "Environment", "ManagedBy"]
  check_doc_name   = "${var.project}-check"
  check_doc_arn    = "arn:aws:ssm:${local.region}:${local.account_id}:document/${local.check_doc_name}"

  # Laboratoire : tout principal du compte autorisé à assumer sts:AssumeRole peut
  # prendre ces rôles. En production, restreindre au rôle opérateur.
  trust_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = "arn:aws:iam::${local.account_id}:root" }
    }]
  })
}

# Document SSM unique que drift-reader a le droit d'exécuter.
# Contenu provisoire : remplacé par le contrôle Ansible en mode check (US-8).
resource "aws_ssm_document" "check" {
  name            = local.check_doc_name
  document_type   = "Command"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Controle DriftGuard (provisoire, remplace par Ansible en US-8)"
    mainSteps = [{
      action = "aws:runShellScript"
      name   = "check"
      inputs = { runCommand = ["echo driftguard-check"] }
    }]
  })
  tags = local.tags
}

# --------------------------- drift-reader ---------------------------
resource "aws_iam_role" "reader" {
  name               = "drift-reader"
  assume_role_policy = local.trust_policy
  tags               = local.tags
}

resource "aws_iam_role_policy" "reader" {
  name = "drift-reader-policy"
  role = aws_iam_role.reader.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "LectureEc2EtCloudTrail"
        Effect   = "Allow"
        Action   = ["ec2:Describe*", "cloudtrail:LookupEvents", "ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
        Resource = "*"
      },
      {
        Sid    = "LectureBucketApplicatif"
        Effect = "Allow"
        Action = [
          "s3:GetBucket*", "s3:GetEncryptionConfiguration", "s3:GetLifecycleConfiguration",
          "s3:GetReplicationConfiguration", "s3:GetAccelerateConfiguration", "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.app.arn
      },
      {
        Sid      = "LectureDuStateSansVerrou"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = local.state_bucket_arn
      },
      {
        Sid      = "LectureFichierState"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${local.state_bucket_arn}/driftguard/terraform.tfstate"
      },
      {
        Sid    = "LectureIamDuProjet"
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:GetRolePolicy", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
          "iam:ListInstanceProfilesForRole", "iam:GetInstanceProfile", "iam:ListRoleTags", "iam:ListInstanceProfileTags"
        ]
        Resource = [
          "arn:aws:iam::${local.account_id}:role/drift-*",
          "arn:aws:iam::${local.account_id}:role/${var.project}-*",
          "arn:aws:iam::${local.account_id}:instance-profile/${var.project}-*"
        ]
      },
      {
        Sid      = "LectureParametreAmi"
        Effect   = "Allow"
        Action   = "ssm:GetParameter"
        Resource = "arn:aws:ssm:${local.region}::parameter/aws/service/ami-amazon-linux-latest/*"
      },
      {
        Sid      = "LectureDocumentDeControle"
        Effect   = "Allow"
        Action   = ["ssm:DescribeDocument", "ssm:DescribeDocumentPermission", "ssm:GetDocument", "ssm:ListTagsForResource"]
        Resource = local.check_doc_arn
      },
      {
        Sid      = "ExecutionDuSeulDocumentDeControle"
        Effect   = "Allow"
        Action   = "ssm:SendCommand"
        Resource = local.check_doc_arn
      },
      {
        Sid      = "ExecutionSurInstancesDuProjetSeulement"
        Effect   = "Allow"
        Action   = "ssm:SendCommand"
        Resource = "arn:aws:ec2:${local.region}:${local.account_id}:instance/*"
        Condition = {
          StringEquals = { "ssm:resourceTag/Project" = var.project }
        }
      }
    ]
  })
}

# --------------------------- drift-fixer ----------------------------
resource "aws_iam_role" "fixer" {
  name               = "drift-fixer"
  assume_role_policy = local.trust_policy
  tags               = local.tags
}

resource "aws_iam_role_policy" "fixer" {
  name = "drift-fixer-policy"
  role = aws_iam_role.fixer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "LectureMinimaleEc2"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:DescribeTags", "ec2:DescribeSecurityGroups"]
        Resource = "*"
      },
      {
        Sid    = "TagsEc2DuProjetCleGerees"
        Effect = "Allow"
        Action = "ec2:CreateTags"
        Resource = [
          "arn:aws:ec2:${local.region}:${local.account_id}:instance/*",
          "arn:aws:ec2:${local.region}:${local.account_id}:security-group/*"
        ]
        Condition = {
          StringEquals                = { "aws:ResourceTag/Project" = var.project }
          "ForAllValues:StringEquals" = { "aws:TagKeys" = local.managed_tag_keys }
        }
      },
      {
        Sid      = "TagsS3BucketApplicatif"
        Effect   = "Allow"
        Action   = ["s3:GetBucketTagging", "s3:PutBucketTagging"]
        Resource = aws_s3_bucket.app.arn
      }
    ]
  })
}
