# FastAPI Server

## Requirements
- Python 3.11+
- Docker (for Postgres)

## Run Postgres
```bash
docker compose up -d
```

This now starts both Postgres and Centrifugo.

## Install deps
```bash
cd server_py
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

The default `server_py/.env` is meant for the dev container, so its database host should be `db`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/limiarcontrol
```

If you run FastAPI on the host machine instead of inside Docker, change the database host to `localhost` and add these values to `server_py/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
CENTRIFUGO_API_URL=http://localhost:8001/api
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_API_KEY=dev-api-key
```

## Run migrations
```bash
cd server_py
alembic upgrade head
```

## Run the API (port 3000)
```bash
cd server_py
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## Curl examples
```bash
curl http://localhost:3000/api/campaigns

curl -X POST http://localhost:3000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Campaign","system":"DND5E"}'

curl http://localhost:3000/api/campaigns/<id>/role-mode

curl -X PUT http://localhost:3000/api/campaigns/<id>/role-mode \
  -H "Content-Type: application/json" \
  -d '{"roleMode":"GM"}'

curl http://localhost:3000/api/campaigns/<id>/items

curl -X POST http://localhost:3000/api/campaigns/<id>/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Longsword","type":"WEAPON","description":"Steel blade"}'

curl -X POST http://localhost:3000/api/dev/reset

curl http://localhost:3000/api/preferences

curl -X PUT http://localhost:3000/api/preferences \
  -H "Content-Type: application/json" \
  -d '{"selectedCampaignId":"<id>"}'
```
