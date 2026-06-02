#!/bin/bash
# =============================================================================
# Stern OS2 — Nango Provider Provisioning Script
# Crée les intégrations dans Nango self-hosted
# Usage: ./provision-nango.sh [NANGO_URL]
# =============================================================================

NANGO_URL="${1:-http://localhost:3003}"
ENV="dev"

echo "=== Stern OS2 — Nango Provisioning ==="
echo "URL: $NANGO_URL"
echo ""

create_integration() {
  local provider="$1"
  local display="$2"
  local body="$3"

  echo -n "  [$provider] $display ... "

  RESULT=$(curl -s -X POST "$NANGO_URL/api/v1/integrations?env=$ENV" \
    -H "Content-Type: application/json" \
    -d "$body")

  ERROR=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('code',''))" 2>/dev/null)

  if [ -z "$ERROR" ] || [ "$ERROR" = "None" ]; then
    echo "OK"
  elif echo "$ERROR" | grep -q "already_exists"; then
    echo "DEJA EXISTANT (skip)"
  else
    echo "ERREUR: $RESULT"
  fi
}

# ============================================================================
# TIER 1 — API KEY (zero setup, fonctionne immédiatement)
# ============================================================================
echo ""
echo "--- TIER 1: API Key (zero OAuth, immédiat) ---"
echo ""

# GitHub PAT — juste un personal access token
create_integration "github-pat" "GitHub (PAT)" '{
  "provider": "github-pat",
  "displayName": "GitHub"
}'

# Stripe API Key
create_integration "stripe-api-key" "Stripe (API Key)" '{
  "provider": "stripe-api-key",
  "displayName": "Stripe"
}'

# Notion SCIM (API key interne)
create_integration "notion-scim" "Notion (API Key)" '{
  "provider": "notion-scim",
  "displayName": "Notion (Internal)"
}'

# ============================================================================
# TIER 2 — OAuth (nécessite une app dev sur le provider)
# NOTE: Une seule app Google Cloud couvre TOUS les services Google
# ============================================================================
echo ""
echo "--- TIER 2: OAuth (nécessite client_id + client_secret) ---"
echo ""
echo "  Pour créer les intégrations OAuth, il faut:"
echo "  1. Créer une app sur le developer portal du provider"
echo "  2. Callback URL: https://api-stern-os2.ori3com.cloud/oauth/callback"
echo "  3. Fournir client_id et client_secret"
echo ""

# Vérifier si les vars d'env sont définies
if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
  echo "  [Google OAuth credentials detected]"

  GOOGLE_SCOPES_CAL="https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/calendar.events"
  GOOGLE_SCOPES_MAIL="https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.readonly"
  GOOGLE_SCOPES_DRIVE="https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.file"
  GOOGLE_SCOPES_DOCS="https://www.googleapis.com/auth/documents"
  GOOGLE_SCOPES_SHEETS="https://www.googleapis.com/auth/spreadsheets"

  create_integration "google-calendar" "Google Calendar" "{
    \"provider\": \"google-calendar\",
    \"displayName\": \"Google Calendar\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"scopes\": \"$GOOGLE_SCOPES_CAL\"
    }
  }"

  create_integration "google-mail" "Gmail" "{
    \"provider\": \"google-mail\",
    \"displayName\": \"Gmail\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"scopes\": \"$GOOGLE_SCOPES_MAIL\"
    }
  }"

  create_integration "google-drive" "Google Drive" "{
    \"provider\": \"google-drive\",
    \"displayName\": \"Google Drive\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"scopes\": \"$GOOGLE_SCOPES_DRIVE\"
    }
  }"

  create_integration "google-docs" "Google Docs" "{
    \"provider\": \"google-docs\",
    \"displayName\": \"Google Docs\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"scopes\": \"$GOOGLE_SCOPES_DOCS\"
    }
  }"

  create_integration "google-sheet" "Google Sheets" "{
    \"provider\": \"google-sheet\",
    \"displayName\": \"Google Sheets\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GOOGLE_CLIENT_ID\",
      \"client_secret\": \"$GOOGLE_CLIENT_SECRET\",
      \"scopes\": \"$GOOGLE_SCOPES_SHEETS\"
    }
  }"
else
  echo "  GOOGLE_CLIENT_ID/SECRET non définis — skip Google OAuth"
  echo "  → Crée une app sur https://console.cloud.google.com/apis/credentials"
  echo "  → Authorized redirect URI: https://api-stern-os2.ori3com.cloud/oauth/callback"
  echo "  → Puis relance: GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=yyy ./provision-nango.sh"
fi

if [ -n "$GITHUB_CLIENT_ID" ] && [ -n "$GITHUB_CLIENT_SECRET" ]; then
  create_integration "github" "GitHub (OAuth)" "{
    \"provider\": \"github\",
    \"displayName\": \"GitHub (OAuth)\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$GITHUB_CLIENT_ID\",
      \"client_secret\": \"$GITHUB_CLIENT_SECRET\",
      \"scopes\": \"repo,read:user,read:org\"
    }
  }"
else
  echo "  GITHUB_CLIENT_ID/SECRET non définis — skip GitHub OAuth"
fi

if [ -n "$SLACK_CLIENT_ID" ] && [ -n "$SLACK_CLIENT_SECRET" ]; then
  create_integration "slack" "Slack" "{
    \"provider\": \"slack\",
    \"displayName\": \"Slack\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$SLACK_CLIENT_ID\",
      \"client_secret\": \"$SLACK_CLIENT_SECRET\",
      \"scopes\": \"channels:read,chat:write,users:read,files:read\"
    }
  }"
else
  echo "  SLACK_CLIENT_ID/SECRET non définis — skip Slack"
fi

if [ -n "$NOTION_CLIENT_ID" ] && [ -n "$NOTION_CLIENT_SECRET" ]; then
  create_integration "notion" "Notion (OAuth)" "{
    \"provider\": \"notion\",
    \"displayName\": \"Notion\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$NOTION_CLIENT_ID\",
      \"client_secret\": \"$NOTION_CLIENT_SECRET\"
    }
  }"
else
  echo "  NOTION_CLIENT_ID/SECRET non définis — skip Notion OAuth"
fi

if [ -n "$HUBSPOT_CLIENT_ID" ] && [ -n "$HUBSPOT_CLIENT_SECRET" ]; then
  create_integration "hubspot" "HubSpot" "{
    \"provider\": \"hubspot\",
    \"displayName\": \"HubSpot\",
    \"credentials\": {
      \"type\": \"OAUTH2\",
      \"client_id\": \"$HUBSPOT_CLIENT_ID\",
      \"client_secret\": \"$HUBSPOT_CLIENT_SECRET\",
      \"scopes\": \"crm.objects.contacts.read,crm.objects.contacts.write,crm.objects.deals.read\"
    }
  }"
else
  echo "  HUBSPOT_CLIENT_ID/SECRET non définis — skip HubSpot"
fi

# ============================================================================
# VÉRIFICATION
# ============================================================================
echo ""
echo "--- Vérification ---"
echo ""

INTEGRATIONS=$(curl -s "$NANGO_URL/api/v1/integrations?env=$ENV")
COUNT=$(echo "$INTEGRATIONS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null)
echo "Intégrations configurées: $COUNT"
echo ""
echo "$INTEGRATIONS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for i in d.get('data', []):
    print(f\"  ✓ {i.get('uniqueKey', i.get('unique_key','?'))} ({i.get('provider','')})\")
" 2>/dev/null

echo ""
echo "=== Provisioning terminé ==="
