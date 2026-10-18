source ".env"
CODE="${1:?Usage: bash refresh-token.sh <authorization-code>}"
curl -sS -X POST https://accounts.spotify.com/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$CODE&redirect_uri=$SPOTIFY_REDIRECT_URI&client_id=$SPOTIFY_CLIENT_ID&client_secret=$SPOTIFY_CLIENT_SECRET" | jq
