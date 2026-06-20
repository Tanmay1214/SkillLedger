# syntax=docker/dockerfile:1.7
# ---- Deps ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install --no-audit --no-fund; fi

# ---- Builder ----
FROM node:20-alpine AS builder
WORKDIR /app

# NEXT_PUBLIC_API_URL must be present at build time (inlined into client bundle).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- Runtime ----
FROM node:20-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

USER nextjs
EXPOSE 3000

CMD ["npm", "run", "start"]
