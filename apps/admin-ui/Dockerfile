FROM node:24.5.0-alpine3.22 AS build
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/admin-ui/package.json apps/admin-ui/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/web-ui/package.json packages/web-ui/package.json
RUN npm install --global pnpm@10.14.0 \
    && pnpm install --frozen-lockfile
COPY apps/admin-ui apps/admin-ui
COPY packages/api-client packages/api-client
COPY packages/web-ui packages/web-ui
RUN pnpm --filter @specproof/admin-ui build

FROM nginx:1.29.0-alpine3.22
COPY infra/docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/admin-ui/dist /usr/share/nginx/html
EXPOSE 8080
