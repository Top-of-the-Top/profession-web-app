### Это основная монорепа для кода

## Frontend запуск

Дефолтный запуск для деплоя (production static через Nginx):

`docker compose up --build`

Локальный dev-режим фронта (Vite) без изменения базового compose:

`docker compose -f docker-compose.yml -f docker-compose.override.dev.yml up --build frontend-dev`