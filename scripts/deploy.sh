#!/bin/bash

# Deployment script with environment variable validation
# Usage: ./scripts/deploy.sh [stage]

set -e

STAGE=${1:-dev}

# Validate required environment variables
required_vars=("AWS_SOURCE_ACCOUNT" "AWS_TARGET_ACCOUNT")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "❌ Error: Missing required environment variables:"
    printf '   %s\n' "${missing_vars[@]}"
    echo ""
    echo "💡 Solutions:"
    echo "   1. Set them in your shell: export AWS_SOURCE_ACCOUNT=123456789012"
    echo "   2. Create a .env file (see .env.example)"
    echo "   3. Use AWS SSO/profiles that set these automatically"
    exit 1
fi

echo "🚀 Deploying CDK stacks for stage: $STAGE"
echo "   Source Account: $AWS_SOURCE_ACCOUNT"
echo "   Target Account: $AWS_TARGET_ACCOUNT"

# Load .env file if it exists
if [[ -f .env ]]; then
    echo "📄 Loading .env file..."
    set -a
    source .env
    set +a
fi

# Deploy CDK stacks
echo "🔨 Synthesizing CDK app..."
cdk synth --context stage=$STAGE

echo "🚀 Deploying stacks..."
cdk deploy --all --context stage=$STAGE --require-approval never

echo "✅ Deployment completed successfully!"