# These create empty secret containers only. Real key values are never put
# in Terraform (not in a .tf file, not in a .tfvars file, not in state as
# plaintext) — fill them in after `terraform apply` via the AWS CLI or
# console. See the README for the exact commands.

locals {
  secret_names = [
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    "LANGCHAIN_API_KEY",
  ]
}

resource "aws_secretsmanager_secret" "app_secrets" {
  for_each = toset(local.secret_names)
  name     = "${var.project_name}/${each.value}"
}
