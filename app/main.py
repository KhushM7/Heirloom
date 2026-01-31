from fastapi import FastAPI

from app.api.routes import router as qa_router
from app.core.settings import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION,
)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


app.include_router(qa_router, prefix=settings.API_V1_STR)
