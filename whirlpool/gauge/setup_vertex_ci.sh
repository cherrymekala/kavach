#!/usr/bin/env bash
# One-time: let GitHub Actions on cherrymekala/kavach call Vertex AI without a key file.
# Workload Identity Federation: GitHub's OIDC token is exchanged for a short-lived token of a
# service account that can only use Vertex AI, and only this repo can impersonate it.
# Safe to re-run. Needs gcloud (signed in as a project owner) and gh.
set -euo pipefail

PROJECT="${GCP_PROJECT:-kavach-510312}"
REPO="cherrymekala/kavach"
POOL="github"
PROVIDER="kavach-repo"
SA_ID="kavach-evals"
SA="$SA_ID@$PROJECT.iam.gserviceaccount.com"

gcloud config set project "$PROJECT" >/dev/null
PN="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"

gcloud services enable aiplatform.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  iam.googleapis.com --quiet

gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "$SA_ID" --display-name "GitHub Actions: Kavach agent evals"
gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA" \
  --role roles/aiplatform.user --condition=None --quiet >/dev/null

gcloud iam workload-identity-pools describe "$POOL" --location global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL" --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --location global \
  --workload-identity-pool "$POOL" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location global \
    --workload-identity-pool "$POOL" --display-name "cherrymekala/kavach" \
    --issuer-uri "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition "assertion.repository == '$REPO'"

gcloud iam service-accounts add-iam-policy-binding "$SA" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PN/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO" \
  --quiet >/dev/null

gh variable set GCP_WIF_PROVIDER -R "$REPO" \
  -b "projects/$PN/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
gh variable set GCP_EVALS_SA -R "$REPO" -b "$SA"
echo "Vertex AI is ready for the agent-evals workflow ($SA)."
