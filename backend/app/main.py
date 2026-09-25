"""
FastAPI application entry point.

Registers:
- API routers (auth, documents, chat)
- Global exception handler for AppError subclasses
- Health check endpoint
- CORS middleware (open during local dev)
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import auth, documents, chat
from app.core.logger import logger
from app.core.exceptions import AppError

app = FastAPI(title="AI Document Search", version="0.1.0")

# ------------------------------------------------------------------
# CORS — allow all origins in development; restrict in production
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://ragbot-ebon.vercel.app",
        "https://ragbot-zwv0.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Global exception handler
# ------------------------------------------------------------------
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(f"AppError [{exc.status_code}]: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/api/v1/health", tags=["admin"])
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}
