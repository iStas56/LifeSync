#!/bin/bash

echo "Останавливаем и удаляем все запущенные контейнеры..."
docker-compose down

echo "Пересобираем образы..."
docker-compose build

echo "Удаляем неиспользуемые и подвешенные образы..."
docker image prune -f

echo "Запускаем контейнеры..."
docker-compose up