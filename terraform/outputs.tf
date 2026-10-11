output "instance_id" {
  value = aws_instance.web.id
}

output "security_group_id" {
  value = aws_security_group.web.id
}

output "app_bucket" {
  value = aws_s3_bucket.app.bucket
}

output "reader_role_arn" {
  value = aws_iam_role.reader.arn
}

output "fixer_role_arn" {
  value = aws_iam_role.fixer.arn
}
