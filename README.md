# QuickSight CICD Migrations

A CDK-based solution that deploys infrastructure to support QuickSight asset migrations from a source AWS account to a target AWS account.

## Architecture Overview

- **Source Account**: Contains QuickSight resources, S3 bucket, and Lambda function for exporting assets
- **Target Account**: Contains S3 bucket for receiving exported assets and Lambda function for processing them

## Prerequisites

- Node.js (v18 or later)
- Python (3.9 or later)
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS CLI configured with appropriate permissions
- Access to both source and target AWS accounts

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd quicksight-cicd-migrations
npm install
pip install -r requirements.txt
```

### 2. Configure Environment Variables

**Option A: Using .env file (Recommended)**
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual account numbers
# DO NOT commit this file to version control
```

Edit `.env`:
```bash
AWS_SOURCE_ACCOUNT=123456789012  # Your source account ID
AWS_TARGET_ACCOUNT=987654321098  # Your target account ID
```

**Option B: Set environment variables directly**
```bash
# Windows PowerShell
$env:AWS_SOURCE_ACCOUNT="123456789012"
$env:AWS_TARGET_ACCOUNT="987654321098"

# Windows CMD
set AWS_SOURCE_ACCOUNT=123456789012
set AWS_TARGET_ACCOUNT=987654321098

# Linux/macOS/Git Bash
export AWS_SOURCE_ACCOUNT="123456789012"
export AWS_TARGET_ACCOUNT="987654321098"
```

### 3. Configure Your Settings

Edit `configs/dev_config.yaml` to customize:
- Stack names
- S3 bucket names
- Lambda function settings
- Regions

### 4. Deploy Infrastructure

**Using the deployment script (Recommended):**
```bash
# If you have Git Bash or WSL
bash scripts/deploy.sh dev

# If using PowerShell/CMD directly
cdk deploy --all --context stage=dev
```

**Manual deployment:**
```bash
# Synthesize first to check for errors
cdk synth --context stage=dev

# Deploy all stacks
cdk deploy --all --context stage=dev
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_SOURCE_ACCOUNT` | Source AWS account ID where QuickSight resources exist | Yes |
| `AWS_TARGET_ACCOUNT` | Target AWS account ID where assets will be migrated | Yes |
| `STAGE` | Deployment stage (dev, prod, etc.) | No (default: dev) |

### Config File Structure

The configuration is stored in `configs/{stage}_config.yaml`:

```yaml
stackName: quicksight-migrations-infra-dev
awsAccount: "${AWS_SOURCE_ACCOUNT}"    # Loaded from environment
awsRegion: "us-east-1"

bucket:
  name: "quicksight-source-s3-bucket"
  versioned: true

lambda:
  functionName: "quicksight-export-lambda"
  runtime: "python3.10"
  timeout: 180

target:
  awsAccount: "${AWS_TARGET_ACCOUNT}"   # Loaded from environment
  awsRegion: "us-east-1"
  bucket:
    name: "quicksight-target-s3-bucket"
    versioned: true
  allowPutObjectAcl: false
```

## Security Best Practices

### ✅ What's Secure
- AWS account numbers are loaded from environment variables
- `.env` file is in `.gitignore` (never committed)
- S3 buckets have encryption and SSL enforcement
- Cross-account permissions use least privilege principle

### ❌ Never Do This
- Don't hardcode account numbers in config files
- Don't commit `.env` files to version control
- Don't use overly broad IAM permissions

## Deployment Stages

You can deploy to different stages (dev, staging, prod):

```bash
# Deploy to dev (default)
bash scripts/deploy.sh dev

# Deploy to production
bash scripts/deploy.sh prod
```

Each stage uses its own config file: `configs/{stage}_config.yaml`

## Troubleshooting

### Common Issues

**1. Missing Environment Variables**
```
❌ Error: Missing required environment variables: AWS_SOURCE_ACCOUNT
```
**Solution**: Set the required environment variables or create a `.env` file.

**2. CDK Bootstrap Required**
```
❌ Error: This stack uses assets, so the toolkit stack must be deployed
```
**Solution**: Bootstrap CDK in both accounts:
```bash
cdk bootstrap aws://SOURCE-ACCOUNT/us-east-1
cdk bootstrap aws://TARGET-ACCOUNT/us-east-1
```

**3. Permission Denied**
```
❌ Error: User is not authorized to perform: sts:AssumeRole
```
**Solution**: Ensure your AWS credentials have permission to deploy to both accounts.

### Useful Commands

```bash
# Check what will be deployed
cdk diff --context stage=dev

# List all stacks
cdk list --context stage=dev

# Destroy all resources (be careful!)
cdk destroy --all --context stage=dev

# View synthesized CloudFormation
cdk synth --context stage=dev
```

## Project Structure

```
├── app.py                          # CDK app entry point
├── configs/
│   └── dev_config.yaml            # Configuration files
├── src/
│   ├── stacks/
│   │   ├── infra_stack.py         # Source account infrastructure
│   │   └── target_stack.py        # Target account infrastructure
│   ├── cdk_construct/
│   │   └── backend_construct.py   # Reusable CDK constructs
│   └── config/
│       └── load.py                # Configuration loader
├── lambda_src/                     # Lambda function source code
├── scripts/
│   └── deploy.sh                  # Deployment script
├── .env.example                   # Environment variables template
└── requirements.txt               # Python dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]
