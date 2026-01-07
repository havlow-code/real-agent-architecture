"""
FastAPI application for autonomous agent.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from config import settings
from observability import trace_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown."""
    # Startup
    trace_logger.info("Starting Autonomous Agent API")
    settings.validate_api_keys()

    yield

    # Shutdown
    trace_logger.info("Shutting down Autonomous Agent API")


app = FastAPI(
    title="Autonomous Business AI Agent",
    description="Sales & Operations AI Agent with RAG, tools, and autonomous decision-making",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Autonomous Business AI Agent",
        "version": "1.0.0",
        "status": "operational"
    }
