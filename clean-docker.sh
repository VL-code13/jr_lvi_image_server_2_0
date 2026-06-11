#!/bin/bash
echo "🛑 Останавливаем контейнеры..."
docker-compose down

echo "🗑️ Удаляем контейнеры, образы и тома проекта..."
docker-compose down --rmi all --volumes --remove-orphans

echo "🧹 Очищаем глобальный Docker-мусор..."
docker system prune -a --volumes -f

echo "🔥 Очищаем кэш сборки..."
docker builder prune -a -f

echo "✅ Проверка:"
echo "Контейнеры: $(docker ps -aq | wc -l)"
echo "Образы: $(docker images -q | wc -l)"
echo "Тома: $(docker volume ls -q | wc -l)"

echo "🚀 Готово к новой сборке!"