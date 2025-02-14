import logging
import signal
import sys

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from lnlp.loaders.pdf import PDFTextExtractor
from lnlp.managers import SplitterManager
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# HTML template for GPU info display
GPU_INFO_TEMPLATE = """
<html>
    <head>
        <style>
            pre {{
                font-family: monospace;
                white-space: pre;
                padding: 20px;
                background-color: #f5f5f5;
                border-radius: 5px;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <pre>{content}</pre>
    </body>
</html>
"""

app = FastAPI(
    title='Libb-NLP API',
    description='API for text splitting using spaCy and similarity-based methods',
    version='0.1.0'
)


def signal_handler(sig, frame):
    logger.info('Received shutdown signal')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.on_event('startup')
async def startup_event():
    logger.info('Application startup')
    app.state.splitter_manager = SplitterManager()


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Application shutdown')
    if hasattr(app.state, 'splitter_manager'):
        await app.state.splitter_manager.cleanup()


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


class TextRequest(BaseModel):
    text: str
    chunk_size: int = 4000
    chunk_overlap: int = 200


class TextResponse(BaseModel):
    chunks: list[str]


class PDFResponse(BaseModel):
    text: list[str]
    html: str | None = None


@app.post('/split/spacy', response_model=TextResponse)
async def split_text_spacy(request: TextRequest):
    r"""Split text using spaCy with configurable chunk size and overlap.

    Example:
        ```bash
        curl -X POST http://localhost:8000/split/spacy \\
          -H "Content-Type: application/json" \\
          -d '{
            "text": "Your long text here. Multiple sentences...",
            "chunk_size": 4000,
            "chunk_overlap": 200
          }'
        ```
    """
    try:
        logger.info('Processing spaCy text split request')
        splitter = await app.state.splitter_manager.get_spacy_splitter()
        chunks = splitter.split_text(
            request.text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        logger.info(f'Successfully split text into {len(chunks)} chunks')
        return TextResponse(chunks=chunks)
    except Exception as e:
        logger.exception('Error in split_text_spacy')
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/split/similarity', response_model=TextResponse)
async def split_text_similarity(request: TextRequest):
    r"""Split text using semantic similarity-based chunking.

    Example:
        ```bash
        curl -X POST http://localhost:8000/split/similarity \\
          -H "Content-Type: application/json" \\
          -d '{
            "text": "Your long text here. Multiple sentences...",
            "chunk_size": 4000,
            "chunk_overlap": 200
          }'
        ```

    Note: chunk_size and chunk_overlap parameters are ignored for similarity-based splitting
    as it uses semantic similarity to determine chunk boundaries.
    """
    try:
        splitter = await app.state.splitter_manager.get_similarity_splitter()
        chunks = splitter.split_text(request.text)
        return TextResponse(chunks=chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def check_gpu():
    """Check if GPU is available and in use"""
    import torch
    gpu_available = torch.cuda.is_available()
    gpu_count = torch.cuda.device_count() if gpu_available else 0
    current_device = torch.cuda.current_device() if gpu_available else None
    device_name = torch.cuda.get_device_name(current_device) if gpu_available else None

    return {
        'gpu_available': gpu_available,
        'gpu_count': gpu_count,
        'current_device': current_device,
        'device_name': device_name
    }


@app.get('/health')
async def health_check():
    gpu_status = check_gpu()
    return {
        'status': 'healthy',
        'gpu': gpu_status
    }


@app.get('/gpu', response_class=HTMLResponse)
async def gpu_info():
    """Get GPU information directly from nvidia-smi command"""
    import subprocess

    from fastapi.responses import HTMLResponse

    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return HTMLResponse(content=GPU_INFO_TEMPLATE.format(content=result.stdout))
        return HTMLResponse(content=GPU_INFO_TEMPLATE.format(content='Error running nvidia-smi command'))
    except FileNotFoundError:
        return HTMLResponse(content=GPU_INFO_TEMPLATE.format(content='nvidia-smi command not found - No NVIDIA GPU detected'))


@app.post('/extract/pdf', response_model=PDFResponse)
async def extract_pdf(
    file: UploadFile = File(...),
    html: bool = False,
    include_page_numbers: bool = False
):
    r"""Extract text from PDF file with optional HTML formatting.

    Example:
        ```bash
        # Extract plain text
        curl -X POST http://localhost:8000/extract/pdf \\
          -F "file=@document.pdf"

        # Extract with HTML formatting
        curl -X POST http://localhost:8000/extract/pdf \\
          -F "file=@document.pdf" \\
          -F "html=true"

        # Include page numbers
        curl -X POST http://localhost:8000/extract/pdf \\
          -F "file=@document.pdf" \\
          -F "include_page_numbers=true"
        ```
    """
    try:
        # Read uploaded file
        content = await file.read()

        # Initialize extractor
        extractor = PDFTextExtractor(content)

        # Extract text
        text = extractor.extract_lines(include_page_numbers=include_page_numbers)

        # Get HTML if requested
        html_content = None
        if html:
            html_content = extractor.extract_html(include_page_numbers=include_page_numbers)

        return PDFResponse(
            text=text,
            html=html_content
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
