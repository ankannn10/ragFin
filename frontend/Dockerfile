# --------- Base deps ---------
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --frozen-lockfile --silent

# --------- Build ---------
FROM node:18-alpine AS builder
WORKDIR /app
ENV NODE_ENV production
# Accept API URL so it gets inlined at build time
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

# --------- Runtime ---------
FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
ENV PORT 3000
# Copy only the build output and production deps
COPY --from=builder /app .
EXPOSE 3000
CMD ["npm", "start"] 