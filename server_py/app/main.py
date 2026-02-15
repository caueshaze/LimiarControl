from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
  campaigns_router,
  dev_router,
  inventory_router,
  items_router,
  members_router,
  parties_router,
  npcs_router,
  preferences_router,
  role_mode_router,
  sessions_router,
  auth_router,
  me_router,
)
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.logging import RequestLoggingMiddleware

app = FastAPI()

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(role_mode_router, prefix="/api/campaigns", tags=["role-mode"])
app.include_router(items_router, prefix="/api/campaigns", tags=["items"])
app.include_router(inventory_router, prefix="/api/campaigns", tags=["inventory"])
app.include_router(npcs_router, prefix="/api/campaigns", tags=["npcs"])
app.include_router(members_router, prefix="/api/campaigns", tags=["members"])
app.include_router(parties_router, prefix="/api", tags=["parties"])
app.include_router(preferences_router, prefix="/api", tags=["preferences"])
app.include_router(dev_router, prefix="/api/dev", tags=["dev"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(me_router, prefix="/api/me", tags=["me"])
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
def health():
    return {"ok": True}
