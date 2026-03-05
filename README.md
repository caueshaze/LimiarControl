<div align="center">

# ⚔️ LimiarControl

### Real-time TTRPG Campaign Management Platform

*A full-stack web application for Game Masters and players to run tabletop RPG sessions with live dice rolling, inventory management, and real-time collaboration.*

---

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--time-brightgreen?style=flat-square)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

</div>

---

## 📖 Overview

**LimiarControl** is a comprehensive digital companion for tabletop RPG sessions. It bridges the gap between physical table play and digital organization — giving GMs full command-center control while providing players an immersive, reactive board experience.

Built with real-time WebSocket communication at its core, every dice roll, shop event, and session update propagates instantly to all connected participants. Whether you're running a D&D 5e dungeon or a Tormenta 20 adventure, LimiarControl keeps everyone at the same table, anywhere in the world.

### What makes it different

- **Lobby system** — Sessions start in a waiting room; players confirm their presence before the GM launches, with live readiness indicators
- **GM Command Center** — Broadcast dice requests to specific players or the whole party, open/close the in-game shop, and monitor activity in real time
- **Full activity timeline** — Every roll and purchase is stored chronologically, visible to both GMs and players during the session
- **Advantage / Disadvantage** — Roll 2 dice and automatically pick the best or worst result, stored with full transparency in the activity feed
- **Party-centric design** — Campaigns contain parties; parties contain sessions. Clean separation between campaign content and play sessions

---

## ✨ Features

### 🎭 For Game Masters
- **Campaign management** — Create and manage campaigns across 5 RPG systems (D&D 5e, Tormenta 20, Pathfinder 2e, Call of Cthulhu, Custom)
- **Party management** — Invite players, manage membership statuses, view who's online
- **Session control** — Start sessions through a lobby flow, force-start, or end sessions instantly
- **Waiting room** — See which players have confirmed presence before activating the session
- **Dice command center** — Request rolls from specific players or everyone, with a reason, with advantage/disadvantage
- **Shop control** — Open and close the in-game shop as a broadcast command to all players
- **Party inventories** — View any player's inventory live during a session
- **Session activity feed** — Chronological timeline of all rolls and purchases, updated in real time
- **NPC generator** — Create and manage non-player characters with traits, goals, and secrets
- **Item catalog** — Build a campaign item catalog with stats, prices, and descriptions

### ⚔️ For Players
- **Home page alerts** — Instant notification when a GM opens a session or lobby (via WebSocket, not polling)
- **Party menu** — See party members, session history, and your current inventory
- **Session lobby** — Confirm presence and see who's ready before the session starts
- **Live game board** — Receive and respond to GM commands in real time
- **Dice rolling** — Roll virtually (server-side) or manually enter a physical dice result
- **In-game shop** — Browse and purchase items when the GM opens the shop
- **Activity feed** — See all session rolls and purchases on the board
- **Inventory panel** — Quick access to your character's inventory during play

### ⚙️ Platform
- **JWT authentication** — designed for quick table sessions
- **Presence tracking** — Online/offline indicators per campaign room
- **Internationalization** — English and Brazilian Portuguese support
- **Persistent preferences** — Remembers your last campaign selection

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19 + TypeScript | UI framework |
| **Build** | Vite 7 | Dev server & bundler |
| **Styling** | Tailwind CSS 4 | Utility-first styling |
| **State** | TanStack Query 5 | Server state management |
| **Routing** | React Router 7 | Client-side routing |
| **Backend** | FastAPI 0.115 | REST API + WebSocket server |
| **ORM** | SQLModel 0.0.22 | Database models + validation |
| **Database** | PostgreSQL 16 | Persistent storage |
| **Migrations** | Alembic | Schema version control |
| **Real-time** | WebSockets (native) | Live session events |
| **Auth** | HMAC-SHA256 JWT | Stateless authentication |
| **Containers** | Docker + Compose | Local development |

---

## 🏗️ Architecture

```
LimiarControl/
├── src/                          # React frontend (TypeScript)
│   ├── app/
│   │   ├── config/               # Environment & app config
│   │   └── routes/               # Route definitions
│   ├── entities/                 # Core domain types
│   ├── features/                 # Feature modules
│   │   ├── auth/                 # Authentication context & hooks
│   │   ├── campaign-select/      # Campaign selection & provider
│   │   ├── dice-roller/          # Dice rolling (WS-backed)
│   │   ├── party-management/     # Party & invite management
│   │   ├── sessions/             # Session state & WS hooks
│   │   ├── inventory/            # Inventory management
│   │   ├── npc-generator/        # NPC creation & display
│   │   └── shop/                 # In-session shop panel
│   ├── pages/                    # Page-level components
│   │   ├── GmDashboardPage/      # GM command center
│   │   ├── PlayerBoardPage/      # Player game board
│   │   ├── PlayerPartyPage/      # Player party hub
│   │   ├── PlayerHomePage/       # Player home + session alerts
│   │   ├── PartyDetailsPage/     # GM party management
│   │   └── ...                   # Login, Register, Catalog, NPCs...
│   └── shared/
│       ├── api/                  # HTTP repo layer (axios)
│       ├── realtime/             # WebSocket client
│       ├── i18n/                 # Translations (en-US, pt-BR)
│       └── ui/                   # Shared UI components
│
└── server_py/                    # FastAPI backend (Python)
    ├── app/
    │   ├── api/
    │   │   ├── routes/           # REST endpoint handlers
    │   │   │   ├── auth.py       # Register, login, /me
    │   │   │   ├── campaigns.py  # Campaign CRUD + overview
    │   │   │   ├── parties.py    # Party & member management
    │   │   │   ├── sessions.py   # Session lifecycle + commands
    │   │   │   ├── inventory.py  # Inventory operations
    │   │   │   ├── items.py      # Item catalog CRUD
    │   │   │   └── npcs.py       # NPC management
    │   │   ├── ws.py             # WebSocket handlers + room registry
    │   │   └── deps.py           # Dependency injection helpers
    │   ├── models/               # SQLModel database models (14 tables)
    │   ├── schemas/              # Pydantic request/response schemas
    │   ├── core/
    │   │   ├── auth.py           # JWT creation & PIN hashing
    │   │   └── config.py         # Settings from environment
    │   └── main.py               # FastAPI app factory + middleware
    └── alembic/                  # 20+ database migrations
```

---

## 🗄️ Data Model

```
Campaign ──── CampaignMember (GM / PLAYER)
    │
    └── Party ──── PartyMember (invited / joined / declined / left)
          │
          └── Session (LOBBY → ACTIVE → CLOSED)
                │
                ├── RollEvent  (expression, results, label, author)
                └── PurchaseEvent (item, quantity, buyer)

Campaign ──── Item (weapon, armor, consumable, magic, misc)
    │
    └── CampaignMember ──── InventoryItem (quantity, equipped)

User ──── Preferences (selected campaign)
      └── NPC (name, race, role, trait, goal, secret)
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Docker** + Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/your-username/LimiarControl.git
cd LimiarControl
```

### 2. Start the database

```bash
docker compose up -d
```

### 3. Set up the backend

```bash
cd server_py

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env               # Edit as needed

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

### 4. Set up the frontend

```bash
# From the project root
npm install

# Configure environment
cp .env.example .env               # Edit as needed

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**
The API docs will be available at **http://localhost:3000/docs**

---

## ⚙️ Environment Variables

### Frontend — `.env`

```env
VITE_APP_ENV=development
VITE_API_BASE_URL=http://localhost:3000/api
```

### Backend — `server_py/.env`

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
PORT=3000
CORS_ORIGIN=http://localhost:5173
APP_ENV=development
JWT_SECRET=change-me-in-production
```

> ⚠️ **Never commit your `.env` files.** Always change `JWT_SECRET` in production environments.

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive a JWT token |
| `GET` | `/api/auth/me` | Get the authenticated user's profile |

All protected endpoints require:
```
Authorization: Bearer <token>
```

### Campaigns

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/me/campaigns` | List your campaigns |
| `POST` | `/api/campaigns` | Create a campaign |
| `PUT` | `/api/campaigns/:id` | Update a campaign |
| `DELETE` | `/api/campaigns/:id` | Delete a campaign |
| `GET` | `/api/campaigns/:id/overview` | Campaign overview (GM view) |

### Parties & Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/me/parties` | List your parties |
| `GET` | `/api/me/party-invites` | List pending invites |
| `POST` | `/api/parties` | Create a party |
| `GET` | `/api/parties/:id` | Get party details |
| `POST` | `/api/parties/:id/members/me/join` | Accept an invite |
| `POST` | `/api/parties/:id/sessions` | Start a new session |
| `GET` | `/api/parties/:id/sessions/active` | Get the active session |
| `POST` | `/api/sessions/:id/lobby/join` | Confirm lobby presence |
| `POST` | `/api/sessions/:id/lobby/force-start` | Force-start from lobby |
| `POST` | `/api/sessions/:id/commands` | Broadcast a GM command |
| `GET` | `/api/sessions/:id/activity` | Get session activity feed |

### WebSockets

| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/sessions/:sessionId?token=` | Session room (dice rolls, GM commands) |
| `ws://host/ws/campaigns/:campaignId?token=` | Campaign room (presence, session events) |

#### Session WS — client messages
```json
{ "type": "roll", "payload": { "requestId": "...", "expression": "d20", "label": "Perception", "advantage": "advantage" } }
```

#### Session WS — server broadcasts
```json
{ "type": "roll_created", "payload": { ...RollEvent } }
{ "type": "gm_command", "payload": { "command": "request_roll", "data": { "expression": "d20", "targetUserId": "...", "reason": "Stealth check", "mode": "disadvantage" }, "issuedBy": "GM Name" } }
{ "type": "session_closed", "payload": { "endedAt": "..." } }
```

#### Campaign WS — server broadcasts
```json
{ "type": "session_lobby", "payload": { "sessionId": "...", "title": "...", "expectedPlayers": [...] } }
{ "type": "session_started", "payload": {} }
{ "type": "user_online", "payload": { "userId": "...", "displayName": "..." } }
{ "type": "user_offline", "payload": { "userId": "...", "displayName": "..." } }
```

---

## 🎲 Dice Expression Format

LimiarControl supports standard dice notation:

| Expression | Meaning |
|-----------|---------|
| `d20` | Roll 1 twenty-sided die |
| `2d6` | Roll 2 six-sided dice |
| `d20+5` | Roll 1d20, add 5 |
| `3d8-2` | Roll 3d8, subtract 2 |

**Constraints:** count 1–50, sides 1–1000, modifier ±1000

For **advantage / disadvantage**, the server rolls two independent sets and keeps the best or worst result. Both sets are stored in the `results` array for full transparency.

---

## 🗃️ Database Migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/):

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1

# Check current revision
alembic current

# Generate a new migration
alembic revision --autogenerate -m "description"
```

The migration history documents the full schema evolution across 20+ versions, from the initial schema to the lobby system and purchase events.

---

## 🔄 Session Lifecycle

```
GM starts session
      │
      ▼
  [LOBBY] ──► All expected players join  ──► [ACTIVE]
      │                                          │
      └──► GM force-starts               GM ends session
                  │                             │
                  ▼                             ▼
              [ACTIVE]                      [CLOSED]
```

- **LOBBY**: Players see a notification on home and party pages. Each player confirms presence. The GM sees a waiting room with ready/online indicators.
- **ACTIVE**: Full session — dice commands, shop, activity feed all live.
- **CLOSED**: Session ends, players are redirected to home after a short delay.

---

## 🌐 Supported RPG Systems

| ID | System |
|----|--------|
| `DND5E` | Dungeons & Dragons 5th Edition |
| `T20` | Tormenta 20 |
| `PF2E` | Pathfinder 2nd Edition |
| `COC` | Call of Cthulhu |
| `CUSTOM` | Any custom system |

---

## 📦 Production Build

```bash
# Build frontend
npm run build                # Output: dist/

# Run backend in production
uvicorn app.main:app --host 0.0.0.0 --port 3000 --workers 4
```

The `dist/` folder contains the static frontend, ready to be served by nginx, a CDN, or any static file host.

---

## 🤝 Contributing

Contributions are welcome! If you have ideas, bug reports, or want to add features:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push and open a Pull Request

Please keep PRs focused and include a clear description of what changed and why.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ for tabletop adventurers everywhere.

*May your rolls be nat 20s.*

</div>
