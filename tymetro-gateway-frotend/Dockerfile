# Multi-stage build for Vue 3 application

# Stage 1: Build static assets
FROM node:20-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline || npm install
COPY . .
RUN npm run build

# Stage 2: Serve static assets via Nginx
FROM nginx:alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
