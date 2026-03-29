from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session

from app.core.rate_limit import RateLimitMiddleware
from app.api.routes import (
    admin_base_items_router,
    admin_base_spells_router,
    auth_router,
    base_items_router,
    base_spells_router,
    campaign_catalog_router,
    campaign_entities_router,
    campaign_spells_router,
    campaigns_router,
    character_sheet_drafts_router,
    centrifugo_router,
    character_sheets_router,
    combat_router,
    wild_shape_router,
    dev_router,
    inventory_router,
    items_router,
    me_router,
    members_router,
    parties_router,
    preferences_router,
    role_mode_router,
    session_entities_router,
    sessions_router,
    uploads_router,
    users_router,
)
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.logging import RequestLoggingMiddleware
from app.db.migrations import ensure_database_schema
from app.db.session import engine
from app.services.base_item_seeds import bootstrap_base_items_if_empty
from app.services.base_spell_seeds import bootstrap_base_spells_if_empty
from app.services.centrifugo import centrifugo

_is_production = settings.app_env != "development"

app = FastAPI(
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPO_ROOT / "dist"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"
FRONTEND_RESERVED_PREFIXES = {"api", "health", "ws"}

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
):
    details = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422, content={"message": "Validation error", "details": details}
    )


app.include_router(campaigns_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(admin_base_items_router, prefix="/api/admin", tags=["admin-base-items"])
app.include_router(admin_base_spells_router, prefix="/api/admin", tags=["admin-base-spells"])
app.include_router(base_items_router, prefix="/api/base-items", tags=["base-items"])
app.include_router(base_spells_router, prefix="/api/base-spells", tags=["base-spells"])
app.include_router(role_mode_router, prefix="/api/campaigns", tags=["role-mode"])
app.include_router(campaign_catalog_router, prefix="/api/campaigns", tags=["catalog"])
app.include_router(campaign_spells_router, prefix="/api/campaigns", tags=["campaign-spells"])
app.include_router(items_router, prefix="/api/campaigns", tags=["items"])
app.include_router(inventory_router, prefix="/api/campaigns", tags=["inventory"])
app.include_router(campaign_entities_router, prefix="/api/campaigns", tags=["campaign-entities"])
app.include_router(session_entities_router, prefix="/api", tags=["session-entities"])
app.include_router(members_router, prefix="/api/campaigns", tags=["members"])
app.include_router(parties_router, prefix="/api", tags=["parties"])
app.include_router(character_sheet_drafts_router, prefix="/api", tags=["character-sheet-drafts"])
app.include_router(character_sheets_router, prefix="/api", tags=["character-sheets"])
app.include_router(preferences_router, prefix="/api", tags=["preferences"])
if settings.app_env == "development":
    app.include_router(dev_router, prefix="/api/dev", tags=["dev"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(me_router, prefix="/api/me", tags=["me"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(combat_router, prefix="/api", tags=["combat"])
app.include_router(wild_shape_router, prefix="/api", tags=["wild-shape"])
app.include_router(uploads_router, prefix="/api", tags=["uploads"])
app.include_router(centrifugo_router, prefix="/api", tags=["centrifugo"])
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
def health():
    return {"ok": True}


@app.on_event("startup")
def startup_event() -> None:
    ensure_database_schema()
    with Session(engine) as session:
        bootstrap_base_items_if_empty(session)
        bootstrap_base_spells_if_empty(session)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await centrifugo.close()


def _get_frontend_response(full_path: str = "") -> FileResponse:
    normalized_path = full_path.strip("/")
    if normalized_path:
        first_segment = normalized_path.split("/", 1)[0]
        if first_segment in FRONTEND_RESERVED_PREFIXES:
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = (FRONTEND_DIST_DIR / normalized_path).resolve()
        if FRONTEND_DIST_DIR not in candidate.parents and candidate != FRONTEND_DIST_DIR:
            raise HTTPException(status_code=404, detail="Not Found")
        if candidate.is_file():
            return FileResponse(candidate)

    if not FRONTEND_INDEX.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(FRONTEND_INDEX)


@app.get("/", include_in_schema=False)
def serve_frontend_root():
    return _get_frontend_response()


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    return _get_frontend_response(full_path)
