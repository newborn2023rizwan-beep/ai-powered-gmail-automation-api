from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth.google_auth import router as google_auth_router
from app.api.knowledge_base import router as knowledge_base_router


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="AI Email Automation"
)


# =========================================================
# SESSION
# =========================================================

app.add_middleware(
    SessionMiddleware,
    secret_key="your-super-secret-key-change-this",
    same_site="lax",
    https_only=False,
    max_age=1209600,
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(
    google_auth_router
)

app.include_router(
    knowledge_base_router
)


# =========================================================
# ROOT / HEALTH CHECK
# =========================================================

@app.get("/")
def root():

    return {
        "message": "AI Email Automation API is running"
    }