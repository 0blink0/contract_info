# Used in FROM — must be declared before the first FROM (BuildKit scope).
ARG NODE_IMAGE=node:20-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine
ARG NPM_REGISTRY=https://registry.npmmirror.com

FROM ${NODE_IMAGE} AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set registry "${NPM_REGISTRY}" \
    && (npm ci 2>/dev/null || npm install)

COPY . .

ARG VITE_API_KEY=
ENV VITE_API_KEY=$VITE_API_KEY

RUN npm run build

FROM ${NGINX_IMAGE}

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
