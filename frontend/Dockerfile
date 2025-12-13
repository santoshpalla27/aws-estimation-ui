FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Development mode - code mounted as volume
EXPOSE 3000

CMD ["npm", "run", "dev"]
