data "aws_caller_identity" "current" {}

# Tags de référence : ce sont eux que DriftGuard surveillera et corrigera
locals {
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- Image Amazon Linux 2023 (agent SSM préinstallé) ---
data "aws_ssm_parameter" "ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# --- Accès par SSM uniquement (US-2) ---
resource "aws_iam_role" "ec2" {
  name = "${var.project}-ec2"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-ec2"
  role = aws_iam_role.ec2.name
  tags = local.tags
}

# --- Security Group : aucun port entrant, pas de SSH ---
resource "aws_security_group" "web" {
  name        = "${var.project}-sg"
  description = "Aucun port entrant (acces par SSM uniquement)"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${var.project}-sg" })
}

# --- Instance EC2 avec Nginx ---
resource "aws_instance" "web" {
  ami                    = data.aws_ssm_parameter.ami.value
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  vpc_security_group_ids = [aws_security_group.web.id]

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    encrypted = true
  }

  user_data = <<-EOT
    #!/bin/bash
    dnf install -y nginx
    systemctl enable --now nginx
  EOT

  tags = merge(local.tags, { Name = "${var.project}-web" })
}

# --- Bucket S3 applicatif, privé ---
resource "aws_s3_bucket" "app" {
  bucket        = "${var.project}-app-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # permet un destroy complet (US-3)
  tags          = local.tags
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket                  = aws_s3_bucket.app.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
