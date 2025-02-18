import logging
import signal
import sys

import torch
import time
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from lnlp.api.endpoints import chat, extract, split
from lnlp.services.provider import LLMProvider
from lnlp.services.splitters import SplitterManager
from lnlp.utils.health import health_service
from lnlp.utils.templates import render_health_report, render_metrics_report
from lnlp.utils.metrics import metrics_service
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Middleware to track endpoint metrics
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metric
        metrics_service.track_request(
            path=request.url.path,
            method=request.method,
            duration=duration
        )
        
        return response


app = FastAPI(
    title='Libb-NLP API',
    description='Comprehensive NLP API with text processing, AI integration, and hardware optimization',
    version='0.1.0'
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(split.router)
app.include_router(chat.router)
app.include_router(extract.router)


def signal_handler(sig, frame):
    logger.info('Received shutdown signal')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.on_event('startup')
async def startup_event():
    """Initialize resources on startup"""
    logger.info('Application startup')

    # Initialize services
    app.state.splitter_manager = SplitterManager()
    try:
        # Verify models are available
        logger.info('Verifying models...')
        app.state.splitter_manager.get_spacy_splitter()
        app.state.splitter_manager.get_similarity_splitter()
        logger.info('Models verified successfully')
        # Initialize provider
        app.state.provider = LLMProvider()
    except Exception as e:
        logger.error(f'Error during startup: {e}')
        app.state.provider = None


@app.on_event('shutdown')
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info('Starting application shutdown')
    try:
        # Clean up GPU resources if used
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                logger.info('Cleared GPU cache')
            except Exception as e:
                logger.error(f'Error cleaning GPU cache: {e}')

        # Clean up model resources
        if hasattr(app.state, 'splitter_manager'):
            # Clear any loaded models
            app.state.splitter_manager._spacy_splitter = None
            app.state.splitter_manager._similarity_splitter = None
            logger.info('Cleared splitter models')

        # Clean up provider resources
        if hasattr(app.state, 'provider'):
            app.state.provider = None
            logger.info('Cleared provider instance')

        logger.info('Application shutdown complete')
    except Exception as e:
        logger.error(f'Error during shutdown: {e}')


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': str(exc.detail)}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={'detail': str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={'detail': f'Internal server error: {str(exc)}'}
    )


@app.get('/metrics', response_class=HTMLResponse)
def metrics():
    """Get application metrics as HTML report"""
    return render_metrics_report(metrics_service.get_metrics())


@app.get('/health', response_class=HTMLResponse)
def health_check():
    """Get health status as HTML report"""
    health_data = health_service.get_health_report(app)
    return render_health_report(health_data)
