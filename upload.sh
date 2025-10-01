#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
VIDEO_FILE="/home/mvievard/Vidéos/2025-09-29/ideesnoires.MP4"
TITLE="ideesnoires.mp4"
DESCRIPTION="Reprise de \"Idées noires\" (original : Bernard Lavilliers).
Tous droits réservés aux ayants droit de l'œuvre originale.
Nous ne revendiquons aucun droit sur la composition originale. Cette vidéo est publiée à titre non monétisé / non commercial."

PRIVACY_STATUS="unlisted"             # public | unlisted | private
TAGS='[]'
# TAGS='["reprise","cover","Un autre monde","Téléphone"]'
# TAGS='["cover","reprise","Idées noires","Bernard Lavilliers","musique française"]'


# === 1) Obtenir access token via refresh token ===
# TOKEN_RESP=$(curl -s -X POST \
#   -d "client_id=${CLIENT_ID}" \
#   -d "client_secret=${CLIENT_SECRET}" \
#   -d "refresh_token=${REFRESH_TOKEN}" \
#   -d "grant_type=refresh_token" \
#   "https://oauth2.googleapis.com/token")

# Je l'ai eu ici :
# https://developers.google.com/oauthplayground/?code=4/0AVGzR1C2KzItLLV8Cu1_QhtJMN0gC_W3CGQrqp04nj3TdWU4mT9pqnr99iFBrSI2ZBEGIw&scope=https://www.googleapis.com/auth/youtube.upload
ACCESS_TOKEN=$(cat upload.token)
# ACCESS_TOKEN=$(echo "$TOKEN_RESP" | grep -oP '(?<="access_token": ")[^"]+')
# if [ -z "$ACCESS_TOKEN" ]; then
#   echo "Erreur: impossible d'obtenir access_token. Réponse:"
#   echo "$TOKEN_RESP"
#   exit 1
# fi
# echo "Access token obtenu."

# === 2) Start resumable upload session (metadata) ===
METADATA=$(jq -n \
  --arg title "Idées noires" \
  --arg desc "$DESCRIPTION" \
  --argjson tags "$TAGS" \
  '{snippet: {title: $title, description: $desc, tags: $tags}, status: {privacyStatus: "unlisted"}}')

echo $METADATA
START_RESP_HEADERS=$(mktemp)
RESPONSE=$(mktemp)

curl -s -i -X POST \
  -o "$RESPONSE" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "X-Upload-Content-Length: $(stat -c%s "${VIDEO_FILE}")" \
  -H "X-Upload-Content-Type: $(file --mime-type -b "${VIDEO_FILE}")" \
  --data "$METADATA" \
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status" #\
  > "${START_RESP_HEADERS}"


if [ ! -z "$RESPONSE" ]; then
  echo "Erreur: impossible d'initier la session d'upload. Réponse:"
  echo "-----"
  cat "$RESPONSE"
  exit 1
fi

# Récupérer le header Location
UPLOAD_URL=$(grep -i -m1 '^Location:' "${START_RESP_HEADERS}" | sed -E 's/Location: //I' | tr -d '\r\n')
rm -f "${START_RESP_HEADERS}"

if [ -z "$UPLOAD_URL" ]; then
  echo "Erreur: impossible d'initier la session d'upload. Réponse:"
  echo "-----"
  echo "$START_RESP_HEADERS"
  exit 1
fi
echo "Session d'upload créée : $UPLOAD_URL"

# === 3) Upload du fichier (PUT) ===
# Pour les petites vidéos, on peut envoyer en une seule requête PUT :
curl -X PUT \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Length: $(stat -c%s "${VIDEO_FILE}")" \
  -H "Content-Type: $(file --mime-type -b "${VIDEO_FILE}")" \
  --data-binary @"${VIDEO_FILE}" \
  --progress-bar \
  "${UPLOAD_URL}"

echo "Upload terminé. Vérifie dans ton Studio YouTube."



