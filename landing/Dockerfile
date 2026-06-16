FROM node:22-alpine AS base

# Install pnpm
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# Copy dependency files
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* .npmrc* ./

# Disable minimum release age check
RUN pnpm config set minimum-release-age 0

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy project files
COPY . .

# Build the project
RUN pnpm run build

# Expose Next.js port
EXPOSE 3000

# Run in production
CMD ["pnpm", "start"]
