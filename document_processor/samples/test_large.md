# CI/CD Pipeline Setup Guide

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
