resource "aws_ecs_cluster" "app" {
  name = "${var.project_name}-cluster"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}

# First apply points at ":latest", which won't exist in ECR yet — the ECS
# service will sit with 0 healthy tasks until the first GitHub Actions run
# builds and pushes an image. That's expected, not a bug: infra goes up
# first, then CI/CD ships the app onto it.
resource "aws_ecs_task_definition" "app" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "${aws_ecr_repository.app.repository_url}:latest"
      essential = true
      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]
      environment = [
        { name = "LLM_PROVIDER", value = "openai" },
        { name = "ALLOWED_ORIGINS", value = "http://${aws_lb.app.dns_name}" },
        { name = "LANGFUSE_BASE_URL", value = var.langfuse_base_url },
      ]
      secrets = [
        for name, secret in aws_secretsmanager_secret.app_secrets :
        { name = name, valueFrom = secret.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "app"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_task.id]
    assign_public_ip = true # default VPC subnets are public, no NAT Gateway needed
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http, aws_iam_role_policy.ecs_execution_secrets]

  lifecycle {
    # CI/CD registers new task definition revisions and updates the service
    # directly on every deploy — don't let a later `terraform apply` revert
    # the service back to whatever revision is in this file.
    ignore_changes = [task_definition]
  }
}
