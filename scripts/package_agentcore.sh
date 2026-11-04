#!/usr/bin/env bash
# Copy the agent into the AgentCore runtime folder (workshop Module 5,
# step 3) so mamagate/ stays the single source of truth, then write the
# runtime's pyproject.toml (step 4). Run from the repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/MamaGateDeploy/app/MamaGateAgent"

rm -rf "$APP/mamagate" "$APP/main.py"
mkdir -p "$APP"
cp "$ROOT/main.py" "$APP/main.py"
rsync -a --exclude '__pycache__' "$ROOT/mamagate" "$APP/"

cat > "$APP/pyproject.toml" <<'EOF'
[project]
name = "mamagate-agent"
version = "0.1.0"
description = "MamaGate runtime for Amazon Bedrock AgentCore"
requires-python = ">=3.13"
dependencies = [
    "strands-agents>=1.63.0",
    "bedrock-agentcore>=1.25.3",
    "aws-opentelemetry-distro",
    "boto3",
    "pyyaml",
    "pydantic",
]
EOF
# Render account-specific config from the committed templates.
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export ACCOUNT_ID
envsubst '${ACCOUNT_ID}' < "$ROOT/deploy/runtime-policy.template.json" \
  > "$ROOT/deploy/runtime-policy.json"
envsubst '${ACCOUNT_ID}' \
  < "$ROOT/MamaGateDeploy/agentcore/agentcore.template.json" \
  > "$ROOT/MamaGateDeploy/agentcore/agentcore.json"
mkdir -p "$ROOT/MamaGateDeploy/app/deploy"
cp "$ROOT/deploy/runtime-policy.json" "$ROOT/MamaGateDeploy/app/deploy/"
echo "Packaged MamaGate into $APP"
