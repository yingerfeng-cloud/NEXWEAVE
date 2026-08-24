FROM node:24.19.0-alpine3.23@sha256:244cc2b53f46f9e876304391d17682b0ddae9ac33491f4857e25e35a36ba7995 AS build

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.19.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @nexweave/web...

COPY apps/web apps/web
RUN pnpm --filter @nexweave/web build

FROM nginx:1.31.4-alpine3.24@sha256:db35bfc6b2951e7f8a72db5db120288c127ffaeeb4a6d4b95a26fead017d5913 AS runtime
RUN rm /etc/nginx/conf.d/default.conf
COPY apps/web/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080
