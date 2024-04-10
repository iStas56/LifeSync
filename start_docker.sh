#!/bin/bash

echo "Запускаем докер машину..."
colima start

echo "Запускаем контейнеры..."
docker-compose up