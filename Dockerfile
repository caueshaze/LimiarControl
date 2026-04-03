FROM node:22-alpine AS frontend-build

WORKDIR /app

ARG VITE_APP_ENV=production
ARG VITE_API_BASE_URL=/api
ARG VITE_CENTRIFUGO_URL=ws://localhost:8001/connection/websocket
ARG VITE_ENABLE_MUSIC=true
ARG VITE_ENABLE_MAPS=true

ENV VITE_APP_ENV=${VITE_APP_ENV}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_CENTRIFUGO_URL=${VITE_CENTRIFUGO_URL}
ENV VITE_ENABLE_MUSIC=${VITE_ENABLE_MUSIC}
ENV VITE_ENABLE_MAPS=${VITE_ENABLE_MAPS}

COPY package*.json ./
RUN npm ci

COPY index.html ./
COPY vite.config.ts ./
COPY tsconfig*.json ./
COPY postcss.config.js ./
COPY tailwind.config.js ./
COPY public ./public
COPY src ./src

RUN npm run build

FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

COPY server_py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser server_py/ ./
COPY --chown=appuser:appuser Base/ /Base/
COPY --from=frontend-build --chown=appuser:appuser /app/dist ./dist

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
