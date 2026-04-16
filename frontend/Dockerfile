# ============================================
# Finance Tracker — Frontend Dockerfile
# ============================================
#
# 💡 CONCEPT: Development vs Production
#    In development: Vite serves files directly with hot reload
#    In production: Vite compiles everything to static HTML/CSS/JS
#
#    The "dev" stage runs `npm run dev` (hot reload)
#    The "prod" stage runs `npm run build` and serves with nginx

# ---- Development stage ----
FROM node:22-alpine AS dev

WORKDIR /app

# Copy package.json first (to cache npm install)
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the code
COPY . .

EXPOSE 5173

# Vite dev server con hot reload
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Production build stage ----
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Production serve stage ----
FROM nginx:alpine AS prod

# Copy the compiled files to the nginx directory
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
