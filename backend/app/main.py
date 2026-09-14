import logging

from fastapi import Depends, FastAPI

from . import auth, migrations, models
from .db import engine
from .routers import auth as auth_router
from .routers import packages
from .routers import settings as settings_router
from .scheduler import start_background_loops

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Package Tracker")

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(
    packages.router,
    prefix="/api/packages",
    tags=["packages"],
    dependencies=[Depends(auth.get_current_user)],
)
app.include_router(
    settings_router.router,
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(auth.get_current_user)],
)


@app.on_event("startup")
async def on_startup():
    models.Base.metadata.create_all(bind=engine)
    migrations.ensure_schema(engine, models.Base)
    start_background_loops()


@app.get("/api/health")
def health():
    return {"status": "ok"}
