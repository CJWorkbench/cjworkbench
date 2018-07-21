set -e

ABSDIR="$(realpath "$(dirname "$0")")"

echo -n 'Launching Postgres... '
docker run -d --network workbenchdocker --name workbench-db -e POSTGRES_USER=cjworkbench -e POSTGRES_PASWORD=cjworkbench -e POSTGRES_DB=cjworkbench postgres:9

echo -n 'Building Django... '
IMAGE=$(docker build .. -q)
echo "$IMAGE"

echo 'Launching Django... '
docker run --rm -it \
  --network workbenchdocker \
  --name workbench-web \
  -e CJW_SECRET_KEY=notasecret \
  -e CJW_SENDGRID_API_KEY=notakey \
  -e CJW_SENDGRID_INVITATION_ID=1 \
  -e CJW_SENDGRID_CONFIRMATION_ID=1 \
  -e CJW_SENDGRID_PASSWORD_CHANGE_ID=1 \
  -e CJW_SENDGRID_PASSWORD_RESET_ID=1 \
  -e CJW_MOCK_EMAIL=true \
  -p 127.0.0.1:8000:8000 \
  -v "$ABSDIR"/docker-data/importedmodules:/app/importedmodules \
  -v "$ABSDIR"/docker-data/media:/app/media \
  -v "$ABSDIR"/docker-data/secrets:/app/secrets \
  "$IMAGE"
