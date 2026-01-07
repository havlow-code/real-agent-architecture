"""
Main entry point for running the autonomous agent server.
"""

import uvicorn
from config import settings
from jobs import job_scheduler


def main():
    """Start the agent server."""
    # Start background job scheduler
    job_scheduler.start()

    # Run FastAPI server
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # Set to False in production
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
