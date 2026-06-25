FROM node:20-alpine AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json tsconfig.tooling.json eslint.config.js vitest.config.ts vitest.setup.ts .npmrc ./
COPY marketing/package.json ./marketing/package.json
COPY portal/package.json ./portal/package.json
COPY docs/package.json ./docs/package.json
COPY shared/api/package.json ./shared/api/package.json
COPY shared/config/package.json ./shared/config/package.json
COPY shared/types/package.json ./shared/types/package.json
COPY shared/ui/package.json ./shared/ui/package.json
COPY shared/utils/package.json ./shared/utils/package.json

RUN pnpm install --frozen-lockfile --prod=false

COPY . .

ARG VITE_API_BASE_URL=http://localhost:5621
ARG VITE_API_VERSION=v1
ARG VITE_APP_ENVIRONMENT=development

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_VERSION=$VITE_API_VERSION
ENV VITE_APP_ENVIRONMENT=$VITE_APP_ENVIRONMENT

RUN pnpm --filter @charity-status/portal build

FROM nginx:1.27-alpine

COPY --from=build /app/portal/dist /usr/share/nginx/html
