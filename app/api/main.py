from fastapi import APIRouter

from api.routes import data_extraction, data_retrieval

api_router = APIRouter()
api_router.include_router(data_extraction.router)
api_router.include_router(data_retrieval.router)
