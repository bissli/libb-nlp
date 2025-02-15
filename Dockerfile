FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install software-properties-common -y \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy all application code
COPY pyproject.toml README.md install.py ./

# Install Python dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    python install.py --gpu

# Copy application code
COPY src/lnlp ./lnlp

# Set environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Run the application
CMD ["uvicorn", "lnlp.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--reload", "--log-level", "info", "--no-use-colors", "--no-access-log"]
