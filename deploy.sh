#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="kyc-automation-service"
REGION="us-central1"
SERVICE_ACCOUNT="kyc-automation-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Starting Deployment for Blockpass KYC Automation..."

# 1. Enable APIs
echo "✅ Enabling Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    sheets.googleapis.com \
    gmail.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com

# 2. Create Service Account
echo "👤 Creating Service Account..."
gcloud iam service-accounts create kyc-automation-sa \
    --display-name="KYC Automation Service Account" || true

# 3. Assign Permissions
echo "🔐 Assigning IAM Permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/logging.logWriter"

# Note: Sheets and Gmail permissions must be granted manually via Google Workspace Admin 
# or by sharing the Sheet/Granting Delegation to the Service Account.

# 4. Create Secrets (Placeholders - User must fill them)
echo "🔑 Creating Secret Placeholders..."
secrets=("BLOCKPASS_API_KEY" "BLOCKPASS_CLIENT_ID" "SHEET_ID" "GMAIL_USER" "STAKEHOLDER_EMAIL")

for secret in "${secrets[@]}"; do
    gcloud secrets create $secret --replication-policy="automatic" || echo "Secret $secret already exists"
done

echo "⚠️  ACTION REQUIRED: Please add your API keys to Secret Manager using:"
echo "echo -n 'YOUR_KEY' | gcloud secrets versions add [SECRET_NAME] --data-file=-"

# 5. Build and Deploy to Cloud Run
echo "📦 Building and Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --no-allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

# 6. Set up Cloud Scheduler
echo "⏰ Creating Cloud Scheduler Job..."
gcloud scheduler jobs create http kyc-automation-trigger \
    --schedule="0 9 * * *" \
    --uri="${SERVICE_URL}/" \
    --http-method=POST \
    --oidc-service-account-email=${SERVICE_ACCOUNT} \
    --message-body="{}" \
    --location=${REGION} || true

echo "✨ Deployment Complete!"
echo "Service URL: ${SERVICE_URL}"
