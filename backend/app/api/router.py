from fastapi import APIRouter

from app.api.routes import bom, health, impact, query

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(bom.router, prefix="/bom", tags=["BOM import"])
api_router.include_router(impact.router, prefix="/impact", tags=["impact"])
api_router.include_router(query.router, prefix="/query", tags=["query"])

