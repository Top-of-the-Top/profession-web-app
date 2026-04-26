FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
ARG VITE_ADMINKA_GATEWAY_URL=http://localhost:9000
ENV VITE_ADMINKA_GATEWAY_URL=${VITE_ADMINKA_GATEWAY_URL}
ENV NODE_OPTIONS=--max-old-space-size=4096
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
