import os
import json
import random

base_dir = "/Users/mac/Documents/project/ailearning/document_processor/samples"

# 1. Realistic CSV
csv_content = "hostname,ip_address,os,cpu_cores,ram_gb,role,datacenter\n"
roles = ["web_frontend", "api_gateway", "database_primary", "database_replica", "cache_redis", "message_broker", "worker_node"]
os_list = ["Ubuntu 22.04", "Debian 11", "CentOS 8", "Alpine Linux 3.14", "Amazon Linux 2"]
dcs = ["us-east-1a", "us-east-1b", "eu-central-1", "ap-northeast-1", "ap-southeast-2"]

for i in range(1, 150):
    role = random.choice(roles)
    os_sys = random.choice(os_list)
    dc = random.choice(dcs)
    cpu = random.choice([4, 8, 16, 32, 64])
    ram = cpu * random.choice([2, 4])
    ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    hostname = f"{role.replace('_', '-')}-{dc}-{i:03d}"
    csv_content += f"{hostname},{ip},{os_sys},{cpu},{ram},{role},{dc}\n"

with open(os.path.join(base_dir, "test_large.csv"), "w", encoding="utf-8") as f:
    f.write(csv_content)

# 2. Realistic TXT
txt_content = """System Architecture and Incident Response Playbook
=================================================

Overview
This document outlines the high-level architecture of our global payment gateway platform and the standard operating procedures for critical incidents.

Core Services
1. Transaction API (Node.js/Express)
The Transaction API is the main entry point for all incoming payment requests. It performs schema validation using Zod and forwards the validated payloads to the message broker.

2. Message Broker (Apache Kafka)
We use a 5-node Kafka cluster (version 3.4) to buffer incoming requests. The topics are partitioned by merchant ID to ensure strict ordering of transactions for a single merchant.

3. Payment Processor (Golang)
The Go workers consume messages from Kafka, interact with external banking APIs (Stripe, PayPal, Adyen), and persist the final state into PostgreSQL. Go was chosen for its high concurrency throughput using goroutines.

4. Caching Layer (Redis Cluster)
A Redis cluster is used to cache merchant configurations, API keys, and rate-limiting counters.

Incident Response: Database Failover
In the event of a primary PostgreSQL failure, the PgBouncer connection pool will automatically pause incoming requests. The Patroni daemon will promote the most up-to-date replica to primary. 
Engineers must verify the promotion by checking the `/patroni` API endpoint and monitoring the Grafana dashboard for replication lag.
"""
# Repeat content with variations to make it > 1KB
for i in range(5):
    txt_content += f"\nAppendix {i+1}: Historical Outage 202{i}-0{random.randint(1,9)}\n"
    txt_content += f"During the incident, the API latency spiked to {random.randint(2000, 5000)}ms due to a bottleneck in the {random.choice(['Redis cache', 'Kafka producer', 'Go workers', 'Postgres index'])}. The team resolved this by scaling the deployment from {random.randint(10, 20)} pods to {random.randint(30, 50)} pods via Kubernetes HPA.\n"

with open(os.path.join(base_dir, "test_large.txt"), "w", encoding="utf-8") as f:
    f.write(txt_content)

# 3. Realistic MD
md_content = """# CI/CD Pipeline Setup Guide

This comprehensive guide explains how to configure a robust CI/CD pipeline using GitHub Actions, Docker, and AWS Elastic Container Service (ECS).

## Prerequisites
- An active AWS Account with IAM permissions for ECR and ECS.
- Docker installed locally for building images.
- GitHub repository with administrative access.

## Step 1: Dockerizing the Application

Create a `Dockerfile` in the root of your Node.js project:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

## Step 2: GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Amazon ECS

on:
  push:
    branches:
      - main

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: my-node-app
  ECS_SERVICE: production-service
  ECS_CLUSTER: production-cluster

jobs:
  deploy:
    name: Build & Deploy
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

> **Security Note:** Never hardcode AWS access keys. Always use OIDC (OpenID Connect) for authenticating GitHub Actions with AWS IAM.

## Step 3: Troubleshooting

If the ECS tasks are stuck in the `PENDING` state, check the following:
1. Ensure the ECS cluster has available EC2 instances or Fargate capacity.
2. Verify that the task execution IAM role has `ecr:GetDownloadUrlForLayer` permissions.
3. Check the VPC subnets and ensure they have a route to a NAT Gateway or Internet Gateway.
"""
with open(os.path.join(base_dir, "test_large.md"), "w", encoding="utf-8") as f:
    f.write(md_content)

# 4. Realistic JSON
json_data = {
  "name": "ai-terminal-backend",
  "version": "1.4.2",
  "description": "Enterprise AI Assistant Backend Services",
  "main": "dist/index.js",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "nodemon --watch src -e ts,json --exec ts-node src/index.ts",
    "build": "tsc -p tsconfig.json",
    "lint": "eslint 'src/**/*.{ts,js}' --fix",
    "test": "jest --coverage",
    "docker:build": "docker build -t ai-terminal-backend:latest ."
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "dotenv": "^16.3.1",
    "pg": "^8.11.3",
    "typeorm": "^0.3.17",
    "redis": "^4.6.8",
    "kafkajs": "^2.2.4",
    "zod": "^3.22.2",
    "winston": "^3.10.0",
    "jsonwebtoken": "^9.0.1"
  },
  "devDependencies": {
    "@types/node": "^20.5.9",
    "@types/express": "^4.17.17",
    "@types/cors": "^2.8.13",
    "@types/pg": "^8.10.2",
    "typescript": "^5.2.2",
    "ts-node": "^10.9.1",
    "nodemon": "^3.0.1",
    "jest": "^29.6.4",
    "ts-jest": "^29.1.1",
    "eslint": "^8.48.0",
    "@typescript-eslint/parser": "^6.5.0",
    "@typescript-eslint/eslint-plugin": "^6.5.0",
    "supertest": "^6.3.3"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "author": "Core Platform Team",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/company/ai-terminal-backend.git"
  },
  "cloud_deployment_config": {
    "kubernetes": {
      "namespace": "ai-services",
      "replicas": 3,
      "resources": {
        "requests": {
          "cpu": "500m",
          "memory": "512Mi"
        },
        "limits": {
          "cpu": "1000m",
          "memory": "1024Mi"
        }
      },
      "env_vars": [
        {"name": "NODE_ENV", "value": "production"},
        {"name": "DB_HOST", "valueFrom": "postgres-cluster-rw"},
        {"name": "REDIS_URI", "valueFrom": "redis-cluster-master"}
      ]
    }
  }
}
with open(os.path.join(base_dir, "test_large.json"), "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

# 5. Realistic XML
xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.company.payment</groupId>
    <artifactId>payment-gateway</artifactId>
    <version>3.1.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <name>Payment Gateway Microservice</name>
    <description>Handles 3D Secure authentication and payment routing</description>

    <properties>
        <java.version>17</java.version>
        <spring-boot.version>3.1.3</spring-boot.version>
        <postgresql.version>42.6.0</postgresql.version>
        <hibernate.version>6.2.7.Final</hibernate.version>
        <resilience4j.version>2.1.0</resilience4j.version>
    </properties>

    <dependencies>
        <!-- Spring Boot Starter Web -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>${spring-boot.version}</version>
        </dependency>

        <!-- Spring Data JPA -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
            <version>${spring-boot.version}</version>
        </dependency>

        <!-- PostgreSQL Driver -->
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <version>${postgresql.version}</version>
            <scope>runtime</scope>
        </dependency>

        <!-- Circuit Breaker -->
        <dependency>
            <groupId>io.github.resilience4j</groupId>
            <artifactId>resilience4j-spring-boot3</artifactId>
            <version>${resilience4j.version}</version>
        </dependency>
        
        <!-- Prometheus Metrics -->
        <dependency>
            <groupId>io.micrometer</groupId>
            <artifactId>micrometer-registry-prometheus</artifactId>
            <version>1.11.3</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <version>${spring-boot.version}</version>
            </plugin>
        </plugins>
    </build>
</project>
"""
with open(os.path.join(base_dir, "test_large.xml"), "w", encoding="utf-8") as f:
    f.write(xml_content)

# 6. Realistic HTML
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grafana - Infrastructure Dashboard</title>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #111217; color: #cdd9e5; }
        .dashboard-header { padding: 20px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; }
        .panel-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding: 20px; }
        .panel { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px; }
        .panel-title { font-size: 14px; color: #8b949e; margin-bottom: 10px; text-transform: uppercase; }
        .metric-value { font-size: 32px; font-weight: bold; color: #58a6ff; }
        .metric-danger { color: #f85149; }
        .metric-success { color: #3fb950; }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>Kubernetes Cluster Monitoring (us-east-1)</h1>
        <span>Last updated: 2026-07-22 09:45:12 UTC</span>
    </div>
    <div class="panel-grid">
        <div class="panel">
            <div class="panel-title">Overall Cluster CPU Usage</div>
            <div class="metric-value">64.2%</div>
            <p style="font-size: 12px; color: #8b949e;">Total cores: 1024 | Used: 657.4</p>
        </div>
        <div class="panel">
            <div class="panel-title">API Gateway p99 Latency</div>
            <div class="metric-value metric-danger">245 ms</div>
            <p style="font-size: 12px; color: #8b949e;">Threshold: < 150 ms (Alert active)</p>
        </div>
        <div class="panel">
            <div class="panel-title">Database Active Connections</div>
            <div class="metric-value metric-success">1,204</div>
            <p style="font-size: 12px; color: #8b949e;">Max pool size: 5000 (Healthy)</p>
        </div>
        <div class="panel">
            <div class="panel-title">Kafka Message Throughput</div>
            <div class="metric-value">45,892 msg/s</div>
            <p style="font-size: 12px; color: #8b949e;">Partition spread: 98% balanced</p>
        </div>
        <div class="panel">
            <div class="panel-title">Error Rate (HTTP 5xx)</div>
            <div class="metric-value metric-success">0.04%</div>
            <p style="font-size: 12px; color: #8b949e;">Global baseline: 0.1%</p>
        </div>
        <div class="panel">
            <div class="panel-title">Redis Cache Hit Ratio</div>
            <div class="metric-value">92.8%</div>
            <p style="font-size: 12px; color: #8b949e;">Evictions: 0 in last 24h</p>
        </div>
    </div>
</body>
</html>
"""
with open(os.path.join(base_dir, "test_large.html"), "w", encoding="utf-8") as f:
    f.write(html_content)

print("Realistic large files generated successfully!")
