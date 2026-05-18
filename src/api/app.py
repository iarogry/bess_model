"""
FastAPI Application for Energy System Data Import
Головна FastAPI додаток для імпорту даних енергосистеми
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

from routes import router

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Energy System Data Import API",
    description="API для імпорту параметрів енергосистеми (Form, CSV, JSON)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS middleware для веб-додатків
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # У продакшені обмежити specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTES
# ============================================================================

app.include_router(router)

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """
    API Root - інформація про доступні endpoints
    """
    return {
        "message": "Energy System Data Import API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "import_form": "POST /api/import/form",
            "import_csv": "POST /api/import/csv",
            "import_json": "POST /api/import/json",
            "csv_template": "GET /api/import/templates/csv",
            "json_template": "GET /api/import/templates/json",
            "health": "GET /api/import/health"
        }
    }

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Глобальний обробник помилок"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутрішня помилка сервера"}
    )

# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Інціалізація при запуску"""
    logger.info("🚀 Energy System Import API starting...")
    logger.info("📚 Docs available at http://localhost:8000/docs")
    logger.info("✅ Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Очищення при завершенні"""
    logger.info("🛑 Energy System Import API shutting down...")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Запустити сервер
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
