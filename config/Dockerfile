# Nexus Production Deployment Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        nodejs \
        npm \
        curl \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements
COPY ./packages/server/requirements.txt /app/packages/server/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r packages/server/requirements.txt

# Install Node.js dependencies
WORKDIR /app/packages/ui
COPY ./packages/ui/package*.json ./
RUN npm ci --only=production

# Copy project
WORKDIR /app
COPY . .

# Build frontend
WORKDIR /app/packages/ui
RUN npm run build

# Setup database directory
WORKDIR /app
RUN mkdir -p packages/server/data
RUN touch packages/server/data/reins.db

# Expose ports
EXPOSE 8090
EXPOSE 3000

# Create a supervisor configuration
RUN mkdir -p /etc/supervisor/conf.d/
COPY docker/supervisord.conf /etc/supervisor/conf.d/nexus.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]