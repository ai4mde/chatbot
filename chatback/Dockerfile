# ===========================================================================
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.5.30-python3.13-alpine AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CUDA_VISIBLE_DEVICES="" \
    TORCH_CUDA_ARCH_LIST="None" \
    DISABLE_CUDA="1" \
    PATH="/root/.local/bin:$PATH" \
    TZ=Europe/Amsterdam

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    libgcc \
    libstdc++

# Set work directory
WORKDIR /chatback

# Copy project files
COPY . .

# Install dependencies with pre-built wheels for problematic packages
#RUN uv pip install "asyncpg>=0.29.0,<0.31.0" --only-binary=:all: --system && \
#    uv pip install "argon2-cffi>=21.0.0" --system && \
RUN    uv pip install . --system

# ===========================================================================
# Stage 2: Final image
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.5.30-python3.13-alpine

# Set user ID
ARG USER_ID=1101  # Default value if not provided

# Install runtime dependencies
RUN apk add --no-cache \
    libpq \
    libffi \
    openssl \
    libgcc \
    libstdc++ \
    argon2-libs \
    postgresql-client \
    bash \
    doas

# Create non-root user first
#RUN adduser -D -u ${USER_ID} -s /bin/bash cbuser
# Create non-root user and required directories
RUN adduser -D -u ${USER_ID} -s /bin/bash cbuser && \
    echo "permit nopass cbuser as root cmd chown args -R cbuser:cbuser /chatback/data" > /etc/doas.d/doas.conf

# Create and set ownership of directories
WORKDIR /chatback
#RUN chown -R cbuser:cbuser /chatback && \
#    chown -R cbuser:cbuser /usr/local/lib/python3.13 && \
#    chown -R cbuser:cbuser /usr/local/bin

# Copy only necessary production files as cbuser
USER cbuser
COPY --chown=cbuser:cbuser . .

# Create config directory and copy env file
#RUN mkdir config
#COPY --chown=cbuser:cbuser ../config/chatback.env /chatback/config/chatback.env

# Copy installed packages from builder
COPY --from=builder --chown=cbuser:cbuser /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder --chown=cbuser:cbuser /usr/local/bin/ /usr/local/bin/

# Expose port
EXPOSE 8000

# Start the application using the start script
ENTRYPOINT ["/bin/bash"]
CMD ["/chatback/scripts/start.sh"]
        