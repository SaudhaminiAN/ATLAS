# Production frontend: Vite build served by Nginx with API proxy config.
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .

# Same-origin API calls via gateway (/api -> api service)
ENV VITE_API_URL=

RUN npm run build

FROM nginx:1.27-alpine

COPY docker/nginx/http-only.conf /etc/nginx/templates/http-only.conf
COPY docker/nginx/https.conf /etc/nginx/templates/https.conf
COPY docker/nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD test -f /usr/share/nginx/html/index.html || exit 1

ENTRYPOINT ["/entrypoint.sh"]
