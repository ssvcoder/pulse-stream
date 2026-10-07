# PulseStream dashboard — built with Vite, served by nginx.
# VITE_WS_URL / VITE_API_URL are baked in at build time (Vite embeds them),
# so pass them as build args pointing at wherever the backend is reachable.
ARG VITE_WS_URL=ws://localhost:8000/ws/metrics
ARG VITE_API_URL=http://localhost:8000

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG VITE_WS_URL
ARG VITE_API_URL
ENV VITE_WS_URL=${VITE_WS_URL} VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
