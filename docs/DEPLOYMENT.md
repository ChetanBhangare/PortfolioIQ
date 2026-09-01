# PortfolioIQ R2.5 Deployment Runbook

PortfolioIQ uses Vercel for Next.js and Amazon ECS Fargate through ECS Express
Mode for FastAPI. App Runner is not selected because AWS closed it to new
customers. Express Mode supplies the load balancer, HTTPS endpoint, health checks,
CloudWatch integration, networking, and autoscaling without hand-maintained ECS
service infrastructure. Every command below is manual; this repository creates no
AWS or Vercel resources by itself.

## Production topology

```text
GitHub weekday refresh -> GitHub OIDC refresh role -> S3 Parquet

Browser -> HTTPS -> Vercel Next.js -> HTTPS -> ECS Express/Fargate FastAPI
                                                   -> read-only ECS task role -> S3

GitHub main deployment -> GitHub OIDC deploy role -> ECR -> ECS Express/Fargate
```

Daily data refresh and application deployment are independent. New Parquet and
manifest objects become visible on the next API read; no backend deployment is
required.

## 1. Values used below

Replace shell placeholders before running commands:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=<12-digit-account-id>
export ECR_REPOSITORY=portfolioiq-backend
export ECS_EXPRESS_SERVICE=portfolioiq-backend
export VERCEL_ORIGIN=https://<portfolioiq-project>.vercel.app
```

Never put access keys, secret keys, session tokens, or an `AWS_PROFILE` into ECS,
Vercel, or GitHub repository variables.

## 2. Runtime IAM roles

Create `PortfolioIQBackendRuntimeRole` with
`docs/aws/backend-runtime-trust-policy.json`, then attach an inline policy from
`docs/aws/backend-runtime-s3-policy.json`. It grants only bucket location/listing
and object reads below `portfolioiq-cb-data-2026/portfolioiq/*`.

Create `PortfolioIQECSTaskExecutionRole` with
`docs/aws/ecs-task-execution-trust-policy.json` and attach AWS managed policy:

```text
arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

Create `PortfolioIQECSExpressInfrastructureRole` with
`docs/aws/ecs-express-infrastructure-trust-policy.json` and attach:

```text
arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
```

The task execution role pulls ECR images and writes container logs. The runtime
task role is the only role available to application code and cannot write S3.

## 3. ECR repository and first image

```bash
aws ecr create-repository \
  --repository-name "$ECR_REPOSITORY" \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  --region "$AWS_REGION"

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build --platform linux/amd64 -t portfolioiq-backend:0.3.1 backend
docker tag portfolioiq-backend:0.3.1 \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:0.3.1"
docker push \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:0.3.1"
```

Add an ECR lifecycle rule retaining approximately ten release/commit images.

## 4. ECS Express Mode service

Use the ECS console's Express Mode flow, or adapt this command after the roles and
image exist:

```bash
aws ecs create-express-gateway-service \
  --service-name "$ECS_EXPRESS_SERVICE" \
  --execution-role-arn "arn:aws:iam::$AWS_ACCOUNT_ID:role/PortfolioIQECSTaskExecutionRole" \
  --infrastructure-role-arn "arn:aws:iam::$AWS_ACCOUNT_ID:role/PortfolioIQECSExpressInfrastructureRole" \
  --task-role-arn "arn:aws:iam::$AWS_ACCOUNT_ID:role/PortfolioIQBackendRuntimeRole" \
  --primary-container "{\"image\":\"$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:0.3.1\",\"containerPort\":8000,\"environment\":[{\"name\":\"APP_ENV\",\"value\":\"production\"},{\"name\":\"PORT\",\"value\":\"8000\"},{\"name\":\"STORAGE_MODE\",\"value\":\"s3\"},{\"name\":\"AWS_REGION\",\"value\":\"$AWS_REGION\"},{\"name\":\"S3_BUCKET\",\"value\":\"portfolioiq-cb-data-2026\"},{\"name\":\"S3_PREFIX\",\"value\":\"portfolioiq\"},{\"name\":\"CORS_ALLOWED_ORIGINS\",\"value\":\"$VERCEL_ORIGIN\"}]}" \
  --cpu 1024 --memory 2048 \
  --health-check-path /health \
  --scaling-target '{"minTaskCount":1,"maxTaskCount":2,"autoScalingMetric":"AVERAGE_CPU","autoScalingTargetValue":70}' \
  --monitor-resources
```

Use a default VPC for the first portfolio deployment. Do not add a NAT Gateway:
its fixed cost is disproportionate here. Record the generated HTTPS endpoint and
verify `/health`, `/ready`, and CloudWatch logs. If a custom API domain is added,
use ACM and an HTTPS listener; never expose a plain-HTTP public frontend API.

## 5. CORS

Production ECS configuration must set the exact Vercel origin:

```text
CORS_ALLOWED_ORIGINS=https://portfolioiq.example.vercel.app
```

Comma-separated preview origins are supported when explicitly trusted. Never use
`*` in production. Update ECS after the final Vercel URL is known, then verify an
allowed and disallowed browser preflight.

## 6. Vercel

1. Import `ChetanBhangare/PortfolioIQ` into Vercel.
2. Set Root Directory to `frontend`.
3. Framework preset: Next.js; install command: `npm ci`; build: `npm run build`.
4. Use Node.js 22.
5. Add production and preview environment variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://<ecs-express-endpoint-or-api-domain>
```

This is a public URL, not a secret. Add no AWS variable or credential to Vercel.
Redeploy the frontend after changing a `NEXT_PUBLIC_*` value because it is embedded
at build time.

## 7. GitHub deployment OIDC

Create `PortfolioIQGitHubDeployRole`; do not reuse the data-refresh role. Replace
`AWS_ACCOUNT_ID`/`AWS_REGION` placeholders in the examples under `docs/aws/`, then
use `github-deploy-trust-policy.json` and
`github-deploy-permissions-policy.json`. The trust permits only `main` in
`ChetanBhangare/PortfolioIQ` and audience `sts.amazonaws.com`.

Create these GitHub repository variables:

```text
AWS_DEPLOY_ROLE_ARN
AWS_REGION
ECR_REPOSITORY
ECS_EXPRESS_SERVICE
ECS_TASK_EXECUTION_ROLE_ARN
ECS_INFRASTRUCTURE_ROLE_ARN
ECS_RUNTIME_ROLE_ARN
S3_BUCKET
S3_PREFIX
CORS_ALLOWED_ORIGINS
```

Keep existing refresh variables and role unchanged. `deploy-backend.yml` runs tests,
builds an immutable commit-SHA image, pushes it to ECR, then updates ECS Express.
Do not attach a GitHub Environment to this job without also revising the OIDC trust:
an Environment changes the token subject. The current trust intentionally matches
only `repo:ChetanBhangare/PortfolioIQ:ref:refs/heads/main`. Pull requests run test
and build workflows only.

## 8. Monitoring and alerts

- ECS service/target health and deployment events provide availability status.
- Express Mode sends container stdout/stderr to CloudWatch Logs.
- JSON request logs contain method, path, status, latency, and request ID only.
- Create CloudWatch alarms for unhealthy target count, HTTP 5xx count, and p95
  target response time. Start with evaluation periods that avoid alerting on a
  single transient request.
- Set log retention to 14 days for this demo rather than retaining indefinitely.
- Configure an AWS Budget email alert at $10 for early warning and another at $30,
  the approximate always-on service baseline. Add 80% forecast alerts where
  available. Budgets alert; they do not automatically stop resources.

## 9. Cost posture

Approximate low-traffic us-east-1 monthly range, before credits:

- ECS Fargate task (0.25–1 vCPU depending final sizing): roughly $9–$30.
- Express-managed Application Load Balancer and public IPv4: roughly $20–$25.
- ECR, CloudWatch, S3 requests/storage, and modest transfer: usually under $1–$5.
- Vercel Hobby: $0 if its eligibility and limits fit; otherwise use the current
  Vercel plan price.
- Expected total: approximately $30–$60/month for an always-on public service.

Benchmark these estimates in AWS Pricing Calculator before creation. Lambda plus
API Gateway can approach $0–$5 at demo traffic but introduces heavy scientific
Python cold starts, adapter packaging, timeout risk, and a second runtime model.
Traditional ECS Fargate requires manual ALB/network/task/service configuration and
has similar underlying cost. App Runner would be operationally simple but is
closed to new AWS customers and has no planned features.

## 10. Rollback

Every deployment pushes both a commit SHA and `latest`; ECS deploys the immutable
SHA. To roll back, redeploy a previously validated SHA from ECR through the manual
workflow or ECS console. Confirm `/health`, then run the smoke script. Vercel keeps
prior deployments; promote the previous successful deployment from its dashboard.
Do not delete prior ECR images until they fall outside the rollback retention set.

## 11. Smoke tests

After deployment:

```bash
python scripts/production_smoke.py \
  --frontend https://<vercel-host> \
  --backend https://<ecs-or-api-host>
```

Then use a desktop browser to run the default portfolio and visit Overview, Risk,
Optimization, and Stress Testing. Confirm charts render and the browser console has
no CORS, mixed-content, or JavaScript errors. Playwright is intentionally deferred:
the seven-check browser flow is small, while installing browsers and maintaining
chart selectors would add disproportionate CI weight. Add one Playwright Chromium
smoke only after stable public URLs exist.

## 12. Troubleshooting and security checklist

- **502/unhealthy target:** container must listen on `0.0.0.0:$PORT`; inspect ECS
  events, target health, and CloudWatch startup logs.
- **AccessDenied from S3:** verify the task role, bucket/prefix, region, and that no
  `AWS_PROFILE` is configured.
- **CORS failure:** compare the browser Origin exactly with
  `CORS_ALLOWED_ORIGINS`; schemes and hostnames must match.
- **Frontend configuration error:** rebuild/redeploy Vercel after setting
  `NEXT_PUBLIC_API_BASE_URL`.
- **Slow optimization:** inspect structured latency logs and ECS CPU/memory before
  changing size or adding caching.
- `.env` remains ignored; images and workflows contain no credentials.
- Production uses IAM task-role credentials and GitHub OIDC only.
- Runtime S3 is read-only; deploy and refresh roles are separate.
- No wildcard production CORS, debug reload, public tracebacks, or portfolio payload
  logging is permitted.
