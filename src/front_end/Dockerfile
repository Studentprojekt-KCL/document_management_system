# -------- Stage 1: Build --------
FROM node:20.19.0-slim AS builder

WORKDIR /app

# Security: Update packages and remove cache
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy only package files first for better caching
COPY package*.json ./

# Install dependencies (including dev deps needed for build)
RUN npm install

# Copy source code
COPY . .

# Build application
RUN npm run build

# Verify build output
RUN test -d dist || (echo "Build failed: dist directory not found" && exit 1)


# -------- Stage 2: Production --------
FROM nginx:stable-alpine

# Security: Update and clean
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# Security: Drop unnecessary capabilities
RUN apk add --no-cache dumb-init

# Create nginx user (already exists in nginx image, but being explicit)
# Create nginx config with security headers
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name _;
    server_tokens off;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss;
    gzip_min_length 1024;
    gzip_vary on;
    gzip_proxied any;
    root /usr/share/nginx/html;
    index index.html;
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
    }
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}
EOF

# Copy built app from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Security: Set proper permissions (nginx runs as nginx user)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Security: Make filesystem read-only where possible
RUN chmod -R 755 /var/cache/nginx /var/log/nginx /var/run && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run/nginx.pid

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

# Security: Run as non-root user
USER nginx

# Use dumb-init to handle signals properly
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["nginx", "-g", "daemon off;"]