from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.stt import router as stt_router
from app.api.v1.endpoints.srs_chat import router as srs_chat_router

api_router = APIRouter()

# Core routes
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(admin_router)
api_router.include_router(stt_router, prefix="/stt", tags=["stt"])
api_router.include_router(srs_chat_router, prefix="/srs-chat", tags=["srs-chat"])


@api_router.get("/health-check")
def health_check():
    return {"status": "ok"}
