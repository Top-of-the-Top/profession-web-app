# Используем легкий Node.js
FROM node:20-alpine

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем package.json и package-lock.json (или yarn.lock)
COPY package*.json ./

# Устанавливаем зависимости
RUN npm ci

# Копируем весь фронт-код
COPY . .

# Экспорт порта Vite
EXPOSE 5173

# Команда по умолчанию для dev-сервера
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
