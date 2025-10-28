FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04 AS build

# Set timezone arg early
ARG TZ=America/New_York

# Install system dependencies including Python
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.0

# Configure Poetry to create venv in project
RUN poetry config virtualenvs.in-project true

# Copy dependency files first (better caching)
COPY pyproject.toml poetry.lock README.md ./

# Install dependencies (poetry creates .venv automatically)
RUN poetry install --only main --no-interaction --no-ansi --no-root

# Copy source code (but don't install package yet - will install in production)
COPY ./src/lnlp ./lnlp

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04 AS production

# Set timezone arg early to avoid cache issues
ARG TZ=America/New_York

# Add build arguments
ARG OPENROUTER_API_KEY
ARG OPENROUTER_REFERER
ARG OPENROUTER_TITLE

# Set environment variables
ENV OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
    OPENROUTER_REFERER=${OPENROUTER_REFERER:-http://localhost:8000} \
    OPENROUTER_TITLE=${OPENROUTER_TITLE:-"Libb-NLP API"} \
    PYTHONUNBUFFERED=1

# Install system dependencies including Python and tzdata
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    tzdata \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from build stage
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/pyproject.toml /app/README.md /app/
COPY --from=build /app/lnlp /app/lnlp

# Use virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install the package in production environment
RUN /app/.venv/bin/pip install --no-deps -e /app

# Download models (separate layer for caching)
RUN /app/.venv/bin/python -c 'from lnlp.services.downloaders import download_spacy_model, download_sentence_transformer; \
    download_spacy_model("en_core_web_sm"); \
    download_sentence_transformer("all-mpnet-base-v2")'

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "lnlp.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info", "--no-use-colors", "--no-access-log"]
