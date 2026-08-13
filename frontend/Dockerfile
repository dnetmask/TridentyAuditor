FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host es obligatorio: por defecto Vite solo escucha en localhost dentro
# del contenedor, lo que lo dejaría inalcanzable desde el host aunque el
# puerto esté publicado en docker-compose.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
