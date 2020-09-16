provider "aws" {}

resource "aws_security_group" "locust_fargate_sg" {
  name = "Locust_Fargate_SG"
  description = "Security Group for Locust Fargate Task"

  ingress {
    from_port = 8089
    protocol = "tcp"
    to_port = 8089
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 5557
    protocol = "tcp"
    to_port = 5557
    cidr_blocks = ["(서브넷 CIDR)", "(서브넷 CIDR)", "(서브넷 CIDR)"]
  }

  ingress {
    from_port = 5558
    protocol = "tcp"
    to_port = 5558
    cidr_blocks = ["(서브넷 CIDR)", "(서브넷 CIDR)", "(서브넷 CIDR)"]
  }

  egress {
    from_port = 0
    protocol = "-1"
    to_port = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ECSTaskExecutionRole_terraform"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_cloudwatch_log_group" "ecs_task_log_group" {
  name = "/ecs/LOCUST"
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  role = aws_iam_role.ecs_task_execution_role.name
}

resource "aws_ecs_cluster" "fargate_load_test_cluster" {
  name = "Fargate_Load_Test_Cluster"
}

resource "aws_ecs_task_definition" "locust_fargate" {
  container_definitions = file("./task-definition.json")
  family = "LOCUST"
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  memory = "2048"
  cpu = "1024"
}

resource "aws_ecs_service" "locust_fargate_master" {
  name = "locust_master"
  cluster = aws_ecs_cluster.fargate_load_test_cluster.id
  task_definition = aws_ecs_task_definition.locust_fargate.arn
  desired_count = 1
  launch_type = "FARGATE"

  network_configuration {
    subnets = ["(서브넷 ID)", "(서브넷 ID)", "(서브넷 ID)"]
    security_groups = [aws_security_group.locust_fargate_sg.id]
    assign_public_ip = true
  }
}