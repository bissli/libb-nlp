FROM ghcr.io/prefix-dev/pixi:latest AS build

WORKDIR /app

# Copy installation files
COPY pyproject.toml pixi.lock ./

# Copy source code
COPY ./src/lnlp ./lnlp

# Install dependencies and package (mock CONDA for pixi)
ENV CONDA_OVERRIDE_CUDA=12.2
RUN pixi install --locked -e prod

# Create shell-hook script
RUN pixi shell-hook -e prod > /shell-hook.sh
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04 AS production

# Set timezone arg early to avoid cache issues
ARG TZ=UTC

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

# Install system dependencies including tzdata
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    tzdata \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy environment and entrypoint from build stage
COPY --from=build /app/.pixi/envs/prod /app/.pixi/envs/prod
COPY --from=build --chmod=0755 /shell-hook.sh /shell-hook.sh
COPY --from=build /app/lnlp /app/lnlp

ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Download models after dependencies are installed
RUN /bin/bash -c "\
    source /shell-hook.sh && \
    python -c 'from lnlp.services.downloaders import download_spacy_model, download_sentence_transformer; \
        download_spacy_model(\"en_core_web_sm\"); \
        download_sentence_transformer(\"all-mpnet-base-v2\")'"

ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]

CMD ["uvicorn", "lnlp.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--reload", "--log-level", "info", "--no-use-colors", "--no-access-log"]
