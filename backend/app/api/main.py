from fastapi import APIRouter

from app.api.routes import data_extraction, data_retrieval, voice

api_router = APIRouter()
api_router.include_router(data_extraction.router)
api_router.include_router(data_retrieval.router)
api_router.include_router(voice.router)
