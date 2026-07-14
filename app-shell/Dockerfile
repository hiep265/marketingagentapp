FROM node:24-alpine

WORKDIR /app

# Install dependencies first for caching
COPY package*.json ./
RUN npm ci

# Copy the rest of the source code
COPY . .

# Build the Next.js production build
RUN npm run build

# Expose port 3000
EXPOSE 3000

ENV PORT=3000
ENV NODE_ENV=production

# Start Next.js server
CMD ["npm", "start"]
