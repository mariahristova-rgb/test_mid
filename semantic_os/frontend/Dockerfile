FROM node:24-alpine AS build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
COPY security/ /app/security/
ARG VITE_API_URL
ARG VITE_AUTH0_DOMAIN
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_AUDIENCE
ENV VITE_API_URL=$VITE_API_URL VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE
RUN npm run check:production-auth && npm run typecheck && npm run build && node scripts/render-production-nginx.mjs
FROM nginxinc/nginx-unprivileged:stable-alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY --from=build /app/frontend/nginx.production.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
