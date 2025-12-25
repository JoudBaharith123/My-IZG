"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import customers, health, reports, routes, zoning
from .config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        # Add root_path for Railway proxy compatibility
        root_path="",
    )
    if settings.frontend_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.frontend_allowed_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Root endpoint for diagnostics
    @app.get("/")
    def root():
        return {
            "service": settings.app_name,
            "status": "running",
            "api_prefix": settings.api_prefix,
            "health": f"{settings.api_prefix}/health",
            "docs": "/docs",
        }
    
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(customers.router, prefix=settings.api_prefix)
    app.include_router(zoning.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    app.include_router(routes.router, prefix=settings.api_prefix)
    return app


app = create_app()
