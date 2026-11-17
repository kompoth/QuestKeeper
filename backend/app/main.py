"""FastAPI app: CORS, exception handlers, and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import CSRF_HEADER_NAME
from app.api.errors import register_exception_handlers
from app.api.routers.auth import router as auth_router
from app.api.routers.entities import router as entities_router
from app.api.routers.sharing import invites_router, permissions_router
from app.api.routers.worlds import router as worlds_router
from app.config import get_frontend_origin

app = FastAPI(title="Questkeeper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_frontend_origin()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", CSRF_HEADER_NAME],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(worlds_router)
app.include_router(entities_router)
app.include_router(permissions_router)
app.include_router(invites_router)
