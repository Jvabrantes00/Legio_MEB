FROM node:24-trixie-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci \
    && mkdir -p /app/.next \
    && chown -R node:node /app
USER node
