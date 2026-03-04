FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

# ── Production ────────────────────────────────────────────────────────────────
FROM base AS production
CMD ["node", "src/index.js"]

# ── Development (nodemon hot reload) ─────────────────────────────────────────
FROM base AS development
RUN npm install --save-dev nodemon
CMD ["node_modules/.bin/nodemon", "src/index.js"]
