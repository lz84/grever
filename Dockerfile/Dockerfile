# Grever Production Deployment Dockerfile
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
        curl \
        supervisor \
        nginx \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements
COPY config/requirements.txt /app/packages/server/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r /app/packages/server/requirements.txt

# Install Node.js dependencies for frontend
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

# Expose ports (backend runs on 8096, nginx on 80)
EXPOSE 8096
EXPOSE 80

# Create supervisor and nginx config directories
RUN mkdir -p /etc/supervisor/conf.d/ /etc/nginx/conf.d/ /var/log/nginx /var/run/nginx

# Copy configuration files
COPY docker/supervisord.conf /etc/supervisor/conf.d/nexus.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8096/ || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
