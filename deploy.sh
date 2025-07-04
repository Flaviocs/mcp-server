#!/bin/bash

# Substitua por seu projeto e região
PROJECT_ID="SEBRAE-SP"
REGION="us-central1"
SERVICE_NAME="mcp-server-rae"

# Configura projeto e região
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Faz o build e envia para o Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Faz o deploy no Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --allow-unauthenticated \
  --port 8001 \
  --set-env-vars PORT=8001,DB_HOST=seu_host_mysql,DB_PORT=3306,DB_USER=root,DB_PASSWORD=teste123,DB_NAME=db_ia_teste,RAE_API_HASH=4BDF114F-1A84-47DC-9640-BAF7C763CF9D,RAE_API_TIMEOUT=10.0,RAE_MAX_ITEMS=100,RAE_CACHE_TTL=300,RAE_API_URL=https://raeconsultascoletivo.sp.sebrae.com.br/api/BuscarColetivos
