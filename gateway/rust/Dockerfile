# ── Stage 1: Build ──────────────────────────────────────────────────
FROM rust:1.79-slim as builder

WORKDIR /app

# Install build dependencies for sqlx (postgres) and other native libs
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cache dependency builds
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release && rm -rf src

# Copy actual source and build
COPY src/ src/
COPY migrations/ migrations/ 2>/dev/null || true
COPY config/ config/ 2>/dev/null || true

# Touch main.rs to force rebuild of our code (deps are cached)
RUN touch src/main.rs && cargo build --release

# ── Stage 2: Runtime ────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libssl3 \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mining && useradd -r -g mining -s /bin/false mining

WORKDIR /app

# Copy binary
COPY --from=builder /app/target/release/mining-super-agent /usr/local/bin/mining-super-agent

# Copy config files
COPY --from=builder /app/config/ /app/config/ 2>/dev/null || true
COPY --from=builder /app/migrations/ /app/migrations/ 2>/dev/null || true

# Switch to non-root user
USER mining

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["mining-super-agent"]
