# ── Stage 1: build React app ──────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Replace default nginx vhost with our SPA + proxy config
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3002

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget -q -O- http://localhost:3002/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
