FROM node:20.19.0-slim AS builder

WORKDIR /app

# Build
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Verify build output
RUN test -d dist || (echo "Build failed: dist directory not found" && exit 1)


FROM nginx:stable-alpine

# Security: Update and clean
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# Security: Drop unnecessary capabilities
RUN apk add --no-cache dumb-init

COPY --from=builder /app/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/dist /usr/share/nginx/html
COPY env.template.js /usr/share/nginx/html/env.template.js

# Security: Set proper permissions (nginx runs as nginx user)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /etc/nginx/templates /etc/nginx/conf.d && \
    chmod -R 755 /etc/nginx/templates /etc/nginx/conf.d

# Security: Make filesystem read-only where possible
RUN chmod -R 755 /var/cache/nginx /var/log/nginx /var/run && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run/nginx.pid

COPY ./start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

USER nginx

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["./start.sh"]
