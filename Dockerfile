FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

# Add build arguments
ARG OPENAI_API_KEY
ARG ANTHROPIC_API_KEY
ARG OPENROUTER_API_KEY
ARG OPENROUTER_REFERER
ARG OPENROUTER_TITLE

# Set environment variables
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENV OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
ENV OPENROUTER_REFERER=${OPENROUTER_REFERER:-http://localhost:8000}
ENV OPENROUTER_TITLE=${OPENROUTER_TITLE:-"Libb-NLP API"}

# Set working directory
WORKDIR /app

# Add non-root user early
RUN useradd -m -s /bin/bash app

# Install system dependencies
RUN apt-get update && apt-get install software-properties-common -y \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set up cache directory early and set permissions
RUN mkdir -p /root/.cache/libb-nlp && \
    chmod -R 777 /root/.cache/libb-nlp && \
    chown -R app:app /app /root/.cache/libb-nlp

# Copy only dependency files first
COPY pyproject.toml README.md install.sh ./

# Install Python dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    chmod +x install.sh && \
    ./install.sh --gpu

# Download models before copying application code
COPY src/lnlp/services/downloaders.py ./lnlp/services/downloaders.py
RUN mkdir -p ./lnlp/services && \
    touch ./lnlp/services/__init__.py && \
    python -c "from lnlp.services.downloaders import download_spacy_model, download_sentence_transformer; \
    download_spacy_model('en_core_web_sm'); \
    download_sentence_transformer('all-mpnet-base-v2')"

# Now copy application code
COPY src/lnlp ./lnlp

# Set environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Switch to non-root user
USER app

# Run the application
CMD ["uvicorn", "lnlp.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--reload", "--log-level", "info", "--no-use-colors", "--no-access-log"]
