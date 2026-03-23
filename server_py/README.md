# FastAPI Server

## Requirements
- Python 3.11+
- Docker (for Postgres and Centrifugo)

## Run Postgres
```bash
docker compose up -d db centrifugo
```

This starts PostgreSQL on port `5432` and Centrifugo on port `8001`.

## Install deps
```bash
cd server_py
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Use localhost-based values in `server_py/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
AUTO_MIGRATE=true
JWT_SECRET=dev-secret-change-me
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

In development, the API now runs `alembic upgrade head` automatically on startup by default.
Set `AUTO_MIGRATE=false` if you prefer fail-fast behavior instead of automatic upgrades.

## Seed base catalogs

After the schema is up to date, seed the D&D base catalogs used by character creation, shop flows, and campaign spell setup.

Dry-run:

```bash
server_py/.venv/bin/python scripts/import_dnd_base_items.py --dry-run
server_py/.venv/bin/python scripts/import_dnd_base_spells.py --dry-run
```

Execute the imports:

```bash
server_py/.venv/bin/python scripts/import_dnd_base_items.py
server_py/.venv/bin/python scripts/import_dnd_base_spells.py
```

Notes:

- Items are loaded into `base_item` and `base_item_alias`
- Spells are loaded into `base_spell` and `base_spell_alias`
- If `Base/DND5e_Equipamentos.json` is missing, the item importer falls back to synthetic essential gear seeds
- The importers can be rerun safely because they upsert by canonical identity keys

Validated local result:

- `base_item`: 112 rows
- `base_item_alias`: 243 rows
- `base_spell`: 319 rows
- `base_spell_alias`: 319 rows

## Run the API (port 3000)
```bash
cd server_py
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## Combat docs

- Phase 3A spell-combat notes: [docs/combat_spells_phase_3a.md](./docs/combat_spells_phase_3a.md)

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
