# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies from lockfile for reproducible builds
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/build /usr/share/nginx/html
# Template so PORT can be set at runtime (Cloud Run sets PORT=8080)
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
# Runtime config for frontend (API_URL injected at container start)
COPY config.js.template /etc/nginx/config.js.template
RUN rm -f /etc/nginx/conf.d/default.conf

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Cloud Run sets PORT (default 8080)
ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["/docker-entrypoint.sh"]
