#!/bin/bash
# Pulls secrets from SSM Parameter Store and (re)starts the API and Caddy containers.
set -euo pipefail
REGION=us-east-1
get() {
  aws ssm get-parameter --region "$REGION" --with-decryption \
    --name "$1" --query Parameter.Value --output text
}

umask 077
ENV_FILE=$(mktemp)
{
  echo "DATABASE_URL=$(get /journal/DATABASE_URL)"
  echo "OPENAI_API_KEY=$(get /journal/OPENAI_API_KEY)"
  echo "OPENAI_BASE_URL=https://models.github.ai/inference"
  echo "OPENAI_MODEL=openai/gpt-4o-mini"
} > "$ENV_FILE"

docker rm -f journal-api caddy >/dev/null 2>&1 || true

docker run -d --name journal-api --restart unless-stopped \
  --env-file "$ENV_FILE" -p 127.0.0.1:8000:8000 journal-api:latest

docker run -d --name caddy --restart unless-stopped --network host \
  -v /opt/journal/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v caddy_data:/data -v caddy_config:/config caddy:2

shred -u "$ENV_FILE"
echo "Started. Check: docker ps"