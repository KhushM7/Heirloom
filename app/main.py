from fastapi import FastAPI
from core.settings import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION
)


app.add_api_route(
    settings.API_V1_STR,
    lambda: {"message": "Welcome to Heirloom API"},
    methods=["GET"],
)