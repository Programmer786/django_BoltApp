FROM node:20-bookworm-slim

# whatsapp-web.js drives a real (headless) Chromium via puppeteer.
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium fonts-liberation fonts-noto-color-emoji ca-certificates dumb-init \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev

# Media-send fix for whatsapp-web.js 1.34.x vs WhatsApp Web builds from 2026-09-17
# (same patch as the laptop agent). Harmless if a future release already has it.
COPY patch-wwebjs.js ./
RUN node patch-wwebjs.js

COPY index.js ./
RUN mkdir -p /data/session

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "index.js"]
