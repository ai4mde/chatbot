# ===========================================================================
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM oven/bun:1.2.10-alpine AS builder
# Set user ID
ARG USER_ID=1101  # Default value if not provided

# Create group and user
RUN adduser -D -u ${USER_ID} -s /bin/sh cfuser
# Create group and user
#RUN addgroup -g 1101 cfgroup && \
#    adduser -u 1101 -G cfgroup -s /bin/sh -D cfuser

# Set working directory
WORKDIR /chatfront

# Copy package.json first
COPY package.json ./

# Set ownership early
RUN chown cfuser:cfuser /chatfront package.json

# Switch to cfuser before installing
USER cfuser

# Generate bun.lockb and install all dependencies for building
RUN bun install --frozen-lockfile

# Install dependencies including types
RUN bun add -d \
    @types/react \
    @types/node \
    @remix-run/node \
    @remix-run/dev \
    typescript

# Copy application files
COPY --chown=cfuser:cfuser . .

# Build application
RUN bun run build

# ===========================================================================
# Stage 2: Final image
# ---------------------------------------------------------------------------
FROM oven/bun:1.2.10-alpine AS runner

# Set user ID
ARG USER_ID=1101  # Default value if not provided

# Create group and user
RUN adduser -D -u ${USER_ID} -s /bin/sh cfuser

# Set working directory and ownership
WORKDIR /chatfront
RUN chown cfuser:cfuser /chatfront

# Switch to cfuser before installing dependencies
USER cfuser

# Copy built application from builder
COPY --from=builder --chown=cfuser:cfuser /chatfront/package.json ./

# Install only production dependencies as cfuser
RUN bun install --frozen-lockfile --production

COPY --from=builder --chown=cfuser:cfuser /chatfront/build ./build
COPY --from=builder --chown=cfuser:cfuser /chatfront/public ./public

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Expose port
EXPOSE 3000

# Start the application
#CMD ["bun", "start"]
CMD ["bun", "start", "--", "--host", "0.0.0.0", "--port", "3000"]