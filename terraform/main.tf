# =============================================================================
# RAG Chat Template - terraform/main.tf
#
# 教材として「最小の AWS 構成」と「将来想定の繋ぎ先」をコメントで残しておく。
# Phase 7 (AWS 移行) で順に有効化していく前提。
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # ──────────────────────────────────────────────
  # State 管理（将来想定）
  # ──────────────────────────────────────────────
  # 学習段階ではローカル state でも構わないが、
  # 本番運用に向かう際は backend "s3" + DynamoDB Lock に切り替える想定:
  #
  # backend "s3" {
  #   bucket         = "<state-bucket-name>"
  #   key            = "rag-chat-template/terraform.tfstate"
  #   region         = "ap-northeast-1"
  #   dynamodb_table = "<lock-table-name>"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region
}

# =============================================================================
# Variables
# =============================================================================

variable "region" {
  description = "デプロイ対象の AWS リージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project" {
  description = "リソース名に付与するプロジェクト識別子"
  type        = string
  default     = "rag-chat-template"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.20.0.0/16"
}

# =============================================================================
# VPC（最小構成）
#
#   - public/private サブネットを 2 AZ ずつ
#   - NAT ゲートウェイは教材としては 1 個に絞る
#   - 後ほど Phase 7 で:
#       * backend (ECS Fargate / EKS) を private に置く
#       * Bedrock を PrivateLink VPC Endpoint で繋ぐ
#       * RDS for PostgreSQL を private に置く
# =============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "${var.project}-vpc"
    Project = var.project
  }
}

# NOTE: 教材として今は VPC だけ作る。
# サブネット / IGW / NAT / Route Table / SG は Phase 7 で順に追加していく想定。
#
# resource "aws_subnet" "public" { ... }
# resource "aws_subnet" "private" { ... }
# resource "aws_internet_gateway" "main" { ... }
# resource "aws_nat_gateway" "main" { ... }
# resource "aws_route_table" "public" { ... }
# resource "aws_security_group" "backend" { ... }

# =============================================================================
# S3 bucket (backend からのファイル退避用)
#
#   - 教材初期段階では DB に LargeBinary で保管しているが、
#     Phase 7 で「PDF 原本は S3、テキスト/メタはDB」に分離する想定
# =============================================================================

resource "aws_s3_bucket" "documents" {
  bucket = "${var.project}-documents"

  tags = {
    Project = var.project
    Purpose = "rag-source-documents"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# 将来構成（Phase 7 以降で実装する想定。今は雛形コメント）
# =============================================================================

# ──────────────────────────────────────────────
# Bedrock を PrivateLink で繋ぐ (VPC Interface Endpoint)
# ──────────────────────────────────────────────
# 想定:
#   - backend は private subnet で稼働
#   - Bedrock runtime をパブリックインターネットに出さず PrivateLink 経由で呼ぶ
#   - サービス名: com.amazonaws.<region>.bedrock-runtime
#
# resource "aws_vpc_endpoint" "bedrock_runtime" {
#   vpc_id            = aws_vpc.main.id
#   service_name      = "com.amazonaws.${var.region}.bedrock-runtime"
#   vpc_endpoint_type = "Interface"
#   subnet_ids        = aws_subnet.private[*].id
#   security_group_ids = [aws_security_group.backend.id]
#   private_dns_enabled = true
# }

# ──────────────────────────────────────────────
# OpenSearch Vector DB
# ──────────────────────────────────────────────
# - OpenSearch Serverless (vectorsearch collection) を想定
# - backend からは SigV4 で OpenSearch にアクセス
#
# resource "aws_opensearchserverless_security_policy" "rag_encryption" { ... }
# resource "aws_opensearchserverless_security_policy" "rag_network" { ... }
# resource "aws_opensearchserverless_access_policy" "rag_access" { ... }
# resource "aws_opensearchserverless_collection" "rag" {
#   name = "${var.project}-rag"
#   type = "VECTORSEARCH"
# }

# ──────────────────────────────────────────────
# RDS for PostgreSQL（会話履歴）
# ──────────────────────────────────────────────
# 教材初期段階は backend サイドカーの postgres でよいが、
# 本番では RDS に逃がす。
#
# resource "aws_db_subnet_group" "rds" { ... }
# resource "aws_security_group" "rds" { ... }
# resource "aws_db_instance" "rds" {
#   identifier        = "${var.project}-pg"
#   engine            = "postgres"
#   engine_version    = "16"
#   instance_class    = "db.t4g.micro"
#   allocated_storage = 20
#   db_name           = "chat"
#   username          = var.db_username
#   password          = var.db_password
#   skip_final_snapshot    = false
#   vpc_security_group_ids = [aws_security_group.rds.id]
#   db_subnet_group_name   = aws_db_subnet_group.rds.name
# }

# ──────────────────────────────────────────────
# ECS Fargate / EKS で backend を動かす想定
# ──────────────────────────────────────────────
# - ECR にイメージを push
# - ECS タスクロールで Bedrock / S3 / OpenSearch を呼ぶ
# - ALB の前段に Cognito or IAM 認証
#
# resource "aws_ecr_repository" "backend" { ... }
# resource "aws_ecs_cluster" "main" { ... }
# resource "aws_ecs_task_definition" "backend" { ... }
# resource "aws_ecs_service" "backend" { ... }
# resource "aws_lb" "alb" { ... }

# ──────────────────────────────────────────────
# GitHub Actions OIDC
# ──────────────────────────────────────────────
# - GitHub Actions から AWS にロールを引き受ける用途
# - apply / deploy は OIDC + 引き受けロールで行う
#
# data "aws_iam_openid_connect_provider" "github" { url = "https://token.actions.githubusercontent.com" }
# resource "aws_iam_role" "github_actions" { ... }

# =============================================================================
# Outputs
# =============================================================================

output "vpc_id" {
  value       = aws_vpc.main.id
  description = "作成した VPC の ID"
}

output "documents_bucket" {
  value       = aws_s3_bucket.documents.bucket
  description = "RAG 文書原本の格納用 S3 バケット名"
}
